import os
import sys

# alter path so we can import faftests
faftests_path = os.path.abspath("..")

# alter path so we can import webfaf
webfaf_path = os.path.join(os.path.abspath("../.."), "src/webfaf")

sys.path.insert(0, faftests_path)
sys.path.insert(0, webfaf_path)
os.environ["PATH"] = "{0}:{1}".format(webfaf_path, os.environ["PATH"])

import faftests
from webfaf.webfaf_main import app


class WebfafTestCase(faftests.DatabaseCase):

    def setUp(self):
        super(WebfafTestCase, self).setUp()

        app.config["DATABASE"] = self.postgresql.url()
        app.config["SQLALCHEMY_DATABASE_URI"] = self.postgresql.url()
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_ECHO"] = not True
        self.app = app.test_client()

    def tearDown(self):
        super(WebfafTestCase, self).tearDown()
