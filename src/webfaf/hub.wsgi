#!/usr/bin/python3
import os
import sys
import logging

logging.basicConfig(stream=sys.stderr)
os.environ["WEBFAF_ENVIRON_PRODUCTION"] = "1"
sys.path.insert(0, os.path.dirname(__file__))

# We can only import from webfaf once the PYTHONPATH has been set up above.
# pylint: disable=wrong-import-position
from webfaf.webfaf_main import app as application
from webfaf.webfaf_main import import_blueprint_plugins
import_blueprint_plugins(application)
