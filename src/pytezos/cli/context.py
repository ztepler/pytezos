from typing import Any, Dict


class Context:
    def __init__(self) -> None:
        self._ctx: Dict[Any, Any] = {}

    def __getitem__(self, key):
        return self._ctx[key]

    def __setitem__(self, key, value):
        self._ctx[key] = value
