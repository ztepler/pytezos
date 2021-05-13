import hashlib
from fcache.cache import FileCache

class PyTezosCLICache:
    def __init__(self) -> None:
        self._cache = FileCache('pytezos', flag='c')

    def compilation_needed(self, path: str) -> bool:
        with open(path, 'rb') as file:
            contract_hash = hashlib.sha256(file.read()).hexdigest()

        try:
            cache = self._cache['hashes']
        except KeyError:
            cache = self._cache['hashes'] = {}

        if cache.get(path) != contract_hash:
            cache[path] = contract_hash
            return True
        return False

    def compilation_failed(self, path: str) -> None:
        try:
            cache = self._cache['hashes']
        except KeyError:
            cache = self._cache['hashes'] = {}

        if path in cache:
            del cache[path]

    def sync(self) -> None:
        self._cache.sync()
