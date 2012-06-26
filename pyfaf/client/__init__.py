import kobo
import os

def load_config():
    config_env = "CLIENT_CONFIG_FILE"
    config_default = "/etc/faf/client.conf"
    config_file = os.environ.get(config_env, config_default)
    conf = kobo.conf.PyConfigParser()
    conf.load_from_file(config_file)
    return conf
