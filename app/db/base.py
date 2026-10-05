from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    def __getitem__(self, item: str):
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(item)

    def get(self, item: str, default=None):
        if hasattr(self, item):
            val = getattr(self, item)
            return default if val is None else val
        return default

import app.models
