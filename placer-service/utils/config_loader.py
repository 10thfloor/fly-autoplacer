import yaml
import os

class Config:
    _config = None

    @classmethod
    def get_config(cls):
        if cls._config is None:
            config_path = os.path.join('config', 'config.yml')
            with open(config_path, 'r') as file:
                cls._config = yaml.safe_load(file)
        return cls._config
