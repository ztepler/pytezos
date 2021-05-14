from enum import Enum
from genericpath import exists
import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel
from ruamel.yaml import YAML


CONFIG_NAME = 'pytezos.yml'
LOCKFILE_NAME = 'pytezos.lock'
DEFAULT_LIGO_IMAGE = 'ligolang/ligo:0.13.0'
DEFAULT_SMARTPY_IMAGE = 'bakingbad/smartpy-cli:latest'
DEFAULT_SMARTPY_PROTOCOL = 'florence'


class LigoConfig(BaseModel):
    image: str = DEFAULT_LIGO_IMAGE


class SmartPyConfig(BaseModel):
    image: str = DEFAULT_SMARTPY_IMAGE
    protocol: str = DEFAULT_SMARTPY_PROTOCOL


class PyTezosConfig(BaseModel):
    name: str
    description: Optional[str] = None
    license: Optional[str] = None

    ligo: LigoConfig = LigoConfig()
    smartpy: SmartPyConfig = SmartPyConfig()

    @classmethod
    def load(cls) -> 'PyTezosConfig':

        config_path = os.path.join(os.getcwd(), CONFIG_NAME)

        # _logger.info('Loading config from %s', filename)
        with open(config_path) as file:
            raw_config = file.read()

        # _logger.info('Substituting environment variables')
        # for match in re.finditer(ENV_VARIABLE_REGEX, raw_config):
        #     variable, default_value = match.group(1), match.group(2)
        #     value = env.get(variable)
        #     if not default_value and not value:
        #         raise ConfigurationError(f'Environment variable `{variable}` is not set')
        #     placeholder = '${' + variable + ':-' + default_value + '}'
        #     raw_config = raw_config.replace(placeholder, value or default_value)

        json_config = YAML(typ='base').load(raw_config)
        config = cls.parse_obj(json_config)
        return config

    def save(self):
        yaml = YAML()
        yaml.indent(4)
        config_path = os.path.join(os.getcwd(), CONFIG_NAME)
        config_dict = self.dict()
        with open(config_path, 'w+') as file:
            YAML().dump(config_dict, file)


class SourceLang(Enum):
    michelson = 'Michelson'
    smartpy = 'SmartPy'
    ligo = 'LIGO'


ext_to_source_lang = {
    '.tz': SourceLang.michelson,
    '.py': SourceLang.smartpy,
    '.ligo': SourceLang.ligo,
    '.mligo': SourceLang.ligo,
}


class SourceType(Enum):
    contract = 'contract'
    storage = 'storage'
    parameter = 'parameter'
    lambda_ = 'lambda_'
    metadata = 'metadata'


response_to_source_type = {
    'C': SourceType.contract,
    'S': SourceType.storage,
    'P': SourceType.parameter,
    'L': SourceType.lambda_,
    'M': SourceType.metadata,
}


class Source(BaseModel):
    type: SourceType
    lang: SourceLang
    alias: str
    entrypoint: Optional[str] = None


class PyTezosLockfile(BaseModel):
    sources: Dict[str, Source] = {}
    skipped: List[str] = []

    @classmethod
    def load(cls) -> 'PyTezosLockfile':

        lockfile_path = os.path.join(os.getcwd(), LOCKFILE_NAME)

        if not exists(lockfile_path):
            Path(lockfile_path).touch()
        with open(lockfile_path, 'r') as file:
            raw_lockfile = file.read()

        json_lockfile = YAML(typ='base').load(raw_lockfile) or {}
        lockfile = cls.parse_obj(json_lockfile)
        return lockfile

    def save(self) -> None:
        yaml = YAML(typ='base')
        yaml.indent(4)
        lockfile_path = os.path.join(os.getcwd(), LOCKFILE_NAME)
        lockfile_dict = self.dict()
        with open(lockfile_path, 'w+') as file:
            YAML().dump(lockfile_dict, file)
