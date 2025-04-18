# Entity‑Resolution Prototype

A **stream‑oriented entity‑resolution engine** that

* ingests raw records (people, businesses, addresses, …)
* extracts blocking keys (e.g. `first_name+dob`)
* looks up possible matches in constant time
* fuses matching records into a single **Entity** object
* exposes a simple REST interface via **FastAPI**

This repo is purposely small—ideal for demos, coursework, or hack‑weeks—yet mirrors the core ideas used in production‑grade deduplication systems at large data companies.

---

## 1 . How it Works

### 1.1 Data structures  
| Name | Description |
|------|-------------|
| **`Record`** | One raw row coming from your source system. |
| **`Entity`** | The clustered view; holds **all** record IDs plus a multiset of attribute values. |
| **`key_index`** | `dict[str, str]` → maps every *composite key string* to **any** entity‑id that currently owns it. |
| **`dsu_parent`** | Disjoint‑Set (Union‑Find) parent pointers so entity merges cost ~O(α(N)). |

> **Key trick** – we **never rewrite** `key_index` on merges; instead we follow indirection through `dsu_parent` to jump to the current “root” entity.

### 1.2 Resolution algorithm (streaming)

1. **Canonicalise & block** the incoming record → `{pattern_name: key_string}`.
2. **Lookup** each key in `key_index` → collect candidate entity roots.
3. *If none* → create a brand‑new `Entity`, index its keys, done.
4. *Else* → pick a deterministic winner, **union** all others into it.
5. Attach the new record to the surviving entity.
6. Re‑build composite keys for that entity. If any of those keys map to *another* entity root → back to step 4 (fix‑point loop).
7. Insert each (possibly new) key into `key_index` with `setdefault` (insert‑only).

Because every operation is O(1) or amortised O(α(N)), throughput scales linearly with CPU.

---

## 2 . Running Locally

```bash
# Install & run with Poetry
poetry install
poetry run uvicorn entity_resolution.app:app --reload
```

**Sample session (HTTPie)**
```bash
# new person ➜ returns entity‑id
http POST :8000/resolve/individual id=r1 first_name=Alice last_name=Smith birth_date=1990-01-01

# second record fuses into same entity
http POST :8000/resolve/individual id=r2 first_name=Alice middle_name=Jane last_name=Smith birth_date=1990-01-01

# inspect entity
http GET :8000/entity/<ENTITY_ID>

# quick stats
http :8000/stats
```

Run tests with Poetry:
```bash
poetry run pytest -v          # full suite
poetry run pytest -k api -v   # FastAPI integration tests only
```bash
pytest -v        # pure‑Python unit tests
pytest -k api -v # FastAPI integration tests
```

---

## 3 . Scaling Out

### 3.1 Kafka Streams (or Flink)

* **Partition key**: hash of a *high‑recall* key (e.g. `last_name_initial+dob_bucket`). All events for that family hash to the same partition so in‑partition merges stay local.
* **State store**: RocksDB‐backed `KeyValueStore` with two column families (`entities`, `dsu_parent`). `key_index` can be another CF or an in‑memory LRU + changelog.
* **Exactly‑once**: Process each record inside a Kafka transaction; commit the streams task after updating both stores.
* **Rebalancing**: Because every key is insert‑only, changelog compaction is light; rebuilds are fast.

### 3.2 Redis Cluster

* **Hashes/Sets** as the primary store; use a *slot‑hash tag* to keep all structures for a surname bucket on the same shard.
* Lua or RedisGears script encapsulates lookup → union → insert in a single atomic operation.
* Add a TTL on entities to auto‑evict after N days of no inbound records.

### 3.3 High‑volume Tricks

| Challenge | Mitigation |
|-----------|------------|
| **Hot keys** (Smith, Li) | Secondary hashing (`last_name + crc32(dob)`) or HyperLogLog‑driven sampling to split oversize buckets. |
| **RAM blow‑up** | Don’t store every composite key inside the entity—rebuild from attrs on demand (what this prototype already does). |
| **Late data** | Idempotent merges mean you can replay a whole partition without side‑effects. |
| **Backups** | State stores are append‑only and compacted—snapshot to S3 every hour. |

### 3.4 Observability

* Prometheus counters for `records_processed`, `entities_merged`, `keys_created`.
* Latency histogram from Kafka offset → commit.
* Periodic job that walks `entities` to detect long tail of "monster" entities for manual inspection.

---

## 4 . Where to Go Next

* Add **business** and **address** entity types by supplying different `ResolutionConfiguration` patterns.
* Persist state in Postgres or Dynamo for cold‑start recovery.
* Implement a *split* endpoint for human analysts to undo merge mistakes (requires orphaning keys and rebuilding index).
* Push a React front‑end that streams entity updates via WebSockets.

Happy deduplicating! 😊
