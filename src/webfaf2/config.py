import os
from sqlalchemy.engine.url import _parse_rfc1738_args
from pyfaf.config import config, paths
from pyfaf.utils.parse import str2bool
dburl = _parse_rfc1738_args(config["storage.connectstring"])

WEBFAF_DIR = os.path.dirname(__file__)


class Config(object):
    DEBUG = False
    TESTING = False
    SECRET_KEY = 'NOT_A_RANDOM_STRING'
    SQLALCHEMY_DATABASE_URI = dburl
    OPENID_FS_STORE = os.path.join(paths["spool"], "openid_store")
    MAX_CONTENT_LENGTH = int(config["dumpdir.maxdumpdirsize"])
    RSTPAGES_SRC = os.path.join(WEBFAF_DIR, "templates")
    RSTPAGES_RST_SETTINGS = {'initial_header_level': 3}
    ADMINS = config["mail.admins"].split(",")
    MAIL_SERVER = config["mail.server"]
    MAIL_PORT = config["mail.port"]
    MAIL_USERNAME = config["mail.username"] or None
    MAIL_PASSWORD = config["mail.password"] or None


class ProductionConfig(Config):
    DEBUG = str2bool(config["hub2.debug"])
    SECRET_KEY = config["hub2.secret_key"]


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    TESTING = True
    OPENID_FS_STORE = None
