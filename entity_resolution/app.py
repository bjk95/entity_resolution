from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from entity_resolution.resolver.resolver import (
    ResolutionConfiguration,
    Individual,
    ResolverState,
    resolve,
    find_root
)

app = FastAPI(title="Entity‑Resolution API", version="0.1.0")

# --- In‑memory singleton state -------------------------------------------------
STATE = ResolverState(entities={}, key_index={}, dsu_parent={})
CONFIG = ResolutionConfiguration(
    entity_type="individual",
    keys=[
        ["first_name", "last_name", "birth_date"],
        ["middle_name", "last_name", "birth_date"],
        ["first_name", "birth_date"],
    ],
)

# --- Pydantic DTOs -------------------------------------------------------------
class IndividualDTO(BaseModel):
    id: str = Field(..., description="Unique record id")
    prefix: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    suffix: Optional[str] = None
    birth_date: Optional[str] = None  # ISO‑YYYY‑MM‑DD

class ResolveResponse(BaseModel):
    entity_id: str

class EntityResponse(BaseModel):
    id: str
    record_ids: set[str]
    attrs: dict[str, list[str]]

# --- Routes --------------------------------------------------------------------
@app.post("/resolve/individual", response_model=ResolveResponse)
def resolve_individual(dto: IndividualDTO):
    rec = Individual(**dto.model_dump())
    entity_id = resolve(CONFIG, STATE, rec)
    return {"entity_id": entity_id}


@app.get("/entity/{entity_id}", response_model=EntityResponse)
def get_entity(entity_id: str):
    root = find_root(STATE, entity_id) if entity_id in STATE.dsu_parent else entity_id
    ent = STATE.entities.get(root)
    if not ent:
        raise HTTPException(status_code=404, detail="Entity not found")
    # convert attr value sets to sorted lists for JSON friendliness
    attrs = {k: sorted(list(v)) for k, v in ent.attrs.items()}
    return {"id": ent.id, "record_ids": ent.record_ids, "attrs": attrs}


@app.get("/stats")
def stats():
    return {
        "entities": len(STATE.entities),
        "indexed_keys": len(STATE.key_index),
    }

# To run:
#   uvicorn app:app --reload
