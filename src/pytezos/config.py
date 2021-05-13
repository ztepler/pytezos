import os
from typing import Optional
from pydantic import BaseModel
from ruamel.yaml import YAML

CONFIG_NAME = 'pytezos.yml'
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
        config = cls(**json_config)
        return config

    def save(self):
        yaml = YAML()
        yaml.indent(4)
        config_path = os.path.join(os.getcwd(), CONFIG_NAME)
        config_dict = self.dict()
        with open(config_path, 'w+') as file:
            YAML().dump(config_dict, file)
