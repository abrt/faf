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
    OPENID_ENABLED = str2bool(config.get("openid.enabled", "false"))
    OPENID_FS_STORE = os.path.join(paths["spool"], "openid_store")
    PROXY_SETUP = False
    MAX_CONTENT_LENGTH = int(config["dumpdir.maxdumpdirsize"])
    RSTPAGES_SRC = os.path.join(WEBFAF_DIR, "templates")
    RSTPAGES_RST_SETTINGS = {'initial_header_level': 3}
    ADMINS = config.get("mail.admins", "").split(",")
    MAIL_SERVER = config.get("mail.server", "localhost")
    MAIL_PORT = config.get("mail.port", "25")
    MAIL_USERNAME = config.get("mail.username", None)
    MAIL_PASSWORD = config.get("mail.password", None)
    BRAND_TITLE = config.get("hub2.brand_title", "FAF")
    BRAND_SUBTITLE = config.get("hub2.brand_subtitle", "Fedora Analysis Framework")


class ProductionConfig(Config):
    DEBUG = str2bool(config["hub2.debug"])
    PROXY_SETUP = str2bool(config.get("hub2.proxy_setup", "false"))
    SECRET_KEY = config["hub2.secret_key"]


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    TESTING = True
    OPENID_FS_STORE = None
