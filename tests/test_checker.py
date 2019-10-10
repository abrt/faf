#!/usr/bin/python3
# -*- encoding: utf-8 -*-
import unittest
import logging

import faftests

from pyfaf.checker import *



class CheckerTestCase(faftests.TestCase):
    """
    Test pyfaf.checker
    """

    def test_mandatory(self):
        """
        Test if mandatory=False is correctly handled
        """

        chk = DictChecker({
            "key1_mandatory": IntChecker(minval=0, mandatory=True),
            "key2_optional": IntChecker(minval=0, mandatory=False),
            "key3_mandatory": IntChecker(minval=0), #default mandatory=True
        })

        valid1 = {
            "key1_mandatory": 1,
            "key2_optional": 1,
            "key3_mandatory": 1,
        }

        valid2 = {
            "key1_mandatory": 1,
            "key3_mandatory": 1,
        }

        invalid1 = {
            "key1_mandatory": 1,
            "key2_optional": -1,
            "key3_mandatory": 1,
        }

        invalid2 = {
            "key1_mandatory": -1,
            "key3_mandatory": 1,
        }

        chk.check(valid1)
        chk.check(valid2)
        self.assertRaises(CheckError, chk.check, invalid1)
        self.assertRaises(CheckError, chk.check, invalid2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
