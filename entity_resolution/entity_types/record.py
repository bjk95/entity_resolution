from dataclasses import asdict, dataclass

@dataclass
class Record:
    id: str
    
    def to_keys(self, keys: list[list[str]]) -> dict[str, str]:
        attributes = asdict(self)
        result = {}
        for key in keys:
            key_result = []
            for attribute in key:
                key_result.append(attributes[attribute])
            if None in key_result or "" in key_result:
                continue
            else:
                result['_'.join(key)] = '¬'.join(key_result)
        return result

    