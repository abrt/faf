#!/usr/bin/python
# -*- encoding: utf-8 -*-
import os
import logging
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import faftests
from pyfaf.common import FafError
from pyfaf.retrace import addr2line


class RetraceTestCase(faftests.TestCase):
    def setUp(self):
        cwd = os.getcwd()
        os.environ["PATH"] = "{0}:{1}".format(os.path.join(cwd, "bin"),
                                              os.environ["PATH"])
        os.environ["EU_ADDR2LINE_SAMPLE_DIR"] = os.path.join(cwd,
                                                             "retrace_outputs")

    def test_addr2line_unknown_method(self):
        n, f, l = addr2line("last_chance", int("0x3", 16), "debug")[0]
        self.assertEqual(n, "last_chance")
        self.assertEqual(f, "last_chance.c")
        self.assertEqual(l, 2)

        n, f, l = addr2line("last_chance", int("0xf", 16), "debug")[0]
        self.assertEqual(n, "last_chance")
        self.assertEqual(f, "last_chance.c")
        self.assertEqual(l, 2)

        n, f, l = addr2line("third_full", int("0xf", 16), "debug")[0]
        self.assertEqual(n, "third_full")
        self.assertEqual(f, "third_full.c")
        self.assertEqual(l, 13)

        with self.assertRaises(FafError) as cm:
            addr2line("last_chance", 0, "debug")[0]
        self.assertEqual(str(cm.exception),
                        "eu-addr2line cannot find function name")

        with self.assertRaises(FafError) as cm:
            addr2line("last_chance", int("0x10", 16), "debug")[0]
        self.assertEqual(str(cm.exception),
                        "eu-addr2line cannot find function name")

        with self.assertRaises(FafError) as cm:
            addr2line("other_source", int("0xf", 16), "debug")[0]
        self.assertEqual(str(cm.exception),
                        "eu-addr2line cannot find function name")

        with self.assertRaises(FafError) as cm:
            addr2line("other_line", int("0xf", 16), "debug")[0]
        self.assertEqual(str(cm.exception),
                        "eu-addr2line cannot find function name")

    def test_addr2line_complex_method(self):
        syms = addr2line("complex", int("0xffff", 16), "debug")
        self.assertEqual(len(syms), 2)

        n, f, l = syms.pop()
        self.assertEqual(n, "_ZN7WebCore13StorageThread16threadEntryPointEv")
        self.assertEqual(f, "Source/WTF/wtf/MessageQueue.h")
        self.assertEqual(l, 131)

        n, f, l = syms.pop()
        self.assertEqual(n, "waitForMessageFilteredWithTimeout<WTF::MessageQueue<DataType>::waitForMessage() "
                         "[with DataType = WTF::Function<void()>]::__lambda0>")
        self.assertEqual(f, "Source/WTF/wtf/MessageQueue.c")
        self.assertEqual(l, 1234)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
