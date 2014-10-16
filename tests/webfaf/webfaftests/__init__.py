import os
import sys

# alter path so we can import faftests
faftests_path = os.path.abspath("..")

# alter path so we can import webfaf2
webfaf_path = os.path.join(os.path.abspath("../.."), "src/webfaf2")

sys.path.insert(0, faftests_path)
sys.path.insert(0, webfaf_path)
os.environ["PATH"] = "{0}:{1}".format(webfaf_path, os.environ["PATH"])

import faftests
from webfaf2 import webfaf2


class WebfafTestCase(faftests.DatabaseCase):

    def setUp(self):
        super(WebfafTestCase, self).setUp()

        webfaf2.app.config["DATABASE"] = self.dbpath
        webfaf2.app.config["TESTING"] = True
        webfaf2.app.config["SQLALCHEMY_ECHO"] = not True
        self.app = webfaf2.app.test_client()

    def tearDown(self):
        super(WebfafTestCase, self).tearDown()
