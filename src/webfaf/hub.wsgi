#!/usr/bin/python
import os
import sys
import logging

# sqlalchemy dependency is preferred to be explicit
# also required for EL6
import __main__
import pkg_resources
__main__.__requires__ = __requires__ = []
__requires__.append("SQLAlchemy >= 0.8.2")
pkg_resources.require(__requires__)

logging.basicConfig(stream=sys.stderr)
os.environ["WEBFAF_ENVIRON_PRODUCTION"] = "1"
sys.path.insert(0, os.path.dirname(__file__))

from webfaf.webfaf_main import app as application
from webfaf.webfaf_main import import_blueprint_plugins
import_blueprint_plugins(application)
