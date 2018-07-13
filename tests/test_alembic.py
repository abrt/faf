#!/usr/bin/python
# -*- encoding: utf-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import logging

import faftests

import os
import inspect
import sys

if sys.version_info.major == 2:
#Python 2
    from cStringIO import StringIO as BytesIO
else:
#Python 3
    from io import BytesIO

from pyfaf.storage import migrations
from alembic.config import Config
from alembic import command


class AlembicTestCase(faftests.DatabaseCase):

    """
    Test case for migrations by alembic
    """

    def setUp(self):
        super(AlembicTestCase, self).setUp()
        self.basic_fixtures()

    def test_alembic_head(self):
        heads_ = BytesIO()
        alembic_cfg = Config(stdout=heads_)
        alembic_cfg.set_main_option("script_location",
                                    os.path.dirname(inspect.getfile(migrations)))
        command.heads(alembic_cfg)
        heads = heads_.getvalue()
        heads = heads[:-1]

        self.assertNotIn('\n', heads)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
