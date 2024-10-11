import yaml
import os
import threading

class Config:
    _config = None
    _mtime = None
    _lock = threading.Lock()

    @classmethod
    def get_config(cls):
        with cls._lock:
            config_mtime = os.path.getmtime('config.yaml')
            if cls._config is None or cls._mtime != config_mtime:
                with open('config.yaml', 'r') as f:
                    cls._config = yaml.safe_load(f)
                cls._mtime = config_mtime
        return cls._config
