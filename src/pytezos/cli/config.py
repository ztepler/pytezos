from enum import Enum
from genericpath import exists
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel
from pydantic.json import pydantic_encoder
from ruamel.yaml import YAML
from pytezos.cli.utils import r
import re
from os import environ as env


ENV_VARIABLE_REGEX = r'\${([\w]*):-(.*)}'
CONFIG_NAME = 'pytezos.yml'
DEFAULT_LIGO_IMAGE = 'ligolang/ligo:0.13.0'
DEFAULT_SMARTPY_IMAGE = 'bakingbad/smartpy-cli:latest'
DEFAULT_SMARTPY_PROTOCOL = 'florence'


class LigoConfig(BaseModel):
    image: str = DEFAULT_LIGO_IMAGE


class SmartPyConfig(BaseModel):
    image: str = DEFAULT_SMARTPY_IMAGE
    protocol: str = DEFAULT_SMARTPY_PROTOCOL


class GenericJobConfig(BaseModel):
    description: str
    path: str


class PyTezosConfig(BaseModel):
    name: str
    description: Optional[str] = None
    license: Optional[str] = None

    ligo: LigoConfig = LigoConfig()
    smartpy: SmartPyConfig = SmartPyConfig()

    jobs: Dict[str, GenericJobConfig] = {}
    scenarios: Dict[str, List[str]] = {}

    @classmethod
    def load(cls) -> 'PyTezosConfig':

        config_path = os.path.join(os.getcwd(), CONFIG_NAME)

        with open(config_path) as file:
            raw_config = file.read()

        for match in re.finditer(ENV_VARIABLE_REGEX, raw_config):
            variable, default_value = match.group(1), match.group(2)
            value = env.get(variable)
            if not default_value and not value:
                print(r(f'Environment variable `{variable}` is not set'))
                quit(1)
            placeholder = '${' + variable + ':-' + default_value + '}'
            raw_config = raw_config.replace(placeholder, value or default_value)

        json_config = YAML(typ='base').load(raw_config)
        config = cls.parse_obj(json_config)
        return config

    def save(self) -> None:
        yaml = YAML(typ='base')
        yaml.indent(4)
        config_path = os.path.join(os.getcwd(), CONFIG_NAME)
        # NOTE: Hack to dump enums as strings
        config_dict = json.loads(json.dumps(self, default=pydantic_encoder))
        with open(config_path, 'w+') as file:
            YAML().dump(config_dict, file)


class SourceLang(Enum):
    Michelson = 'Michelson'
    SmartPy = 'SmartPy'
    LIGO = 'LIGO'


ext_to_source_lang = {
    '.tz': SourceLang.Michelson,
    '.py': SourceLang.SmartPy,
    '.ligo': SourceLang.LIGO,
    '.mligo': SourceLang.LIGO,
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
