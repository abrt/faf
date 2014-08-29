from sqlalchemy.engine.url import _parse_rfc1738_args
from pyfaf.config import config
dburl = _parse_rfc1738_args(config["storage.connectstring"])


class Config(object):
    DEBUG = False
    TESTING = False
    SECRET_KEY = '@RANDOM_STRING@'
    SQLALCHEMY_DATABASE_URI = dburl


class ProductionConfig(Config):
    pass


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
