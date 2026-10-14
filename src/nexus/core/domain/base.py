from pydantic import BaseModel, ConfigDict, model_validator

class FrozenDict(dict):
    def __setitem__(self, key, value):
        raise TypeError("FrozenDict is immutable")
    def __delitem__(self, key):
        raise TypeError("FrozenDict is immutable")
    def pop(self, *args, **kwargs):
        raise TypeError("FrozenDict is immutable")
    def popitem(self, *args, **kwargs):
        raise TypeError("FrozenDict is immutable")
    def clear(self):
        raise TypeError("FrozenDict is immutable")
    def update(self, *args, **kwargs):
        raise TypeError("FrozenDict is immutable")
    def setdefault(self, *args, **kwargs):
        raise TypeError("FrozenDict is immutable")

def deep_freeze(obj):
    if isinstance(obj, dict) and not isinstance(obj, FrozenDict):
        return FrozenDict({k: deep_freeze(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return tuple(deep_freeze(v) for v in obj)
    return obj

class FrozenBaseModel(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    @model_validator(mode='after')
    def _freeze_nested_structures(self):
        for field_name in type(self).model_fields.keys():
            value = getattr(self, field_name)
            frozen_val = deep_freeze(value)
            if value is not frozen_val:
                object.__setattr__(self, field_name, frozen_val)
        return self
