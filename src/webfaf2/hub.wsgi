#!/usr/bin/python
import os
import sys
import logging

logging.basicConfig(stream=sys.stderr)
os.environ["WEBFAF_ENVIRON_PRODUCTION"] = "1"
sys.path.insert(0, os.path.dirname(__file__))

from webfaf2 import app as application
