from os.path import isfile

from pytezos.rpc import ShellQuery, mainnet, alphanet, zeronet
from pytezos.crypto import Key
from pytezos.encoding import is_key

default_shell = 'alphanet'
default_key = 'edsk33N474hxzA4sKeWVM6iuGNGDpX2mGwHNxEA4UbWS8sW3Ta3NKH'  # please, use responsibly


class Interop:

    def __init__(self, shell=None, key=None):
        if shell is None:
            shell = default_shell

        if isinstance(shell, str):
            networks = {
                'mainnet': mainnet,
                'alphanet': alphanet,
                'zeronet': zeronet
            }
            self.shell = networks[shell]
        elif isinstance(shell, ShellQuery):
            self.shell = shell
        else:
            raise NotImplementedError(shell)

        if key is None:
            key = default_key

        if isinstance(key, str):
            if is_key(key):
                self.key = Key.from_encoded_key(key)
            elif isfile(key):
                self.key = Key.from_faucet(key)
            else:
                self.key = Key.from_alias(key)
        elif isinstance(key, Key):
            self.key = key
        else:
            raise NotImplementedError(key)

    def _spawn(self, **kwargs):
        raise NotImplementedError

    def using(self, shell: ShellQuery = None, key: Key = None):
        """
        Change current rpc endpoint and account (private key)
        :param shell: one of 'alphanet', 'mainnet', 'zeronet', instance of `ShellQuery`
        :param key: base58 encoded key or instance of `Key`
        :return: A copy of current object with changes applied
        """
        return self._spawn(shell=shell, key=key)
