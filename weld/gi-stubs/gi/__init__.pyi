from typing import Any

def require_version(namespace: str, version: str) -> None: ...

class _Repository:
    def __getattr__(self, name: str) -> Any: ...

repository: _Repository
