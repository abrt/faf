#!/usr/bin/python
# -*- encoding: utf-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import logging

import faftests

from pyfaf.common import import_dir, load_plugins, load_plugin_types

from sample_plugin_dir.base import Base
from sample_plugin_dir.plugin import Sub


class CommonsTestCase(faftests.DatabaseCase):
    """
    Test pyfaf.common
    """

    def test_import_dir(self):
        """
        Test if import_dir imports correct files
        """

        import_dir("sample_plugin_dir", "sample_plugin_dir")

        self.assertEqual(len(Base.__subclasses__()), 1)

    def test_load_plugins(self):
        """
        Test if load_plugins returns correct results
        """

        plugins = load_plugins(Base)
        self.assertIn('sub-plugin', plugins)
        self.assertIs(isinstance(plugins['sub-plugin'], Sub), True)
        self.assertIs(isinstance(plugins['sub-plugin'], Base), True)

    def test_load_plugin_types(self):
        """
        Test if load_plugin_types loads correct classes
        """

        types = load_plugin_types(Base)
        self.assertIn('sub', types)
        self.assertIs(issubclass(types['sub'], Base), True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
