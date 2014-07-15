import os
import sys
import json
import shutil
import datetime
import unittest2 as unittest

# alter path so we can import pyfaf
pyfaf_path = os.path.join(os.path.abspath(".."), "src")
sys.path.insert(0, pyfaf_path)
os.environ["PATH"] = "{0}:{1}".format(pyfaf_path, os.environ["PATH"])

# use separate config file for tests
os.environ["FAF_CONFIG_FILE"] = os.path.join(os.path.abspath("."),
                                             "faftests/test_config.conf")

# create temporary directory for the tests
TEST_DIR = "/tmp/faf_test_data"
if os.path.exists(TEST_DIR):
    shutil.rmtree(TEST_DIR)
os.makedirs(TEST_DIR)


from pyfaf import storage, ureport
from pyfaf.cmdline import CmdlineParser
from pyfaf.utils.contextmanager import captured_output
from pyfaf.storage import fixtures
from pyfaf.storage.symbol import SymbolSource


class TestCase(unittest.TestCase):
    """
    Class that initializes required configuration variables.
    """

    @classmethod
    def tearDownClass(cls):
        """
        Remove temporary directory.
        """

        shutil.rmtree(TEST_DIR)


class DatabaseCase(TestCase):
    """
    Class that provides initialized faf database for the tests.
    """

    @classmethod
    def setUpClass(cls):
        """
        Set up sqlite database in a temp directory.
        Databse created in this step is restored
        for each test.
        """

        super(DatabaseCase, cls).setUpClass()
        cls.dbpath = os.path.join(TEST_DIR, "sqlite.db")
        cls.db = storage.Database(session_kwargs={
                                  "autoflush": False,
                                  "autocommit": False})
        cls.load_data()

        shutil.copy(cls.dbpath, "{0}.clean".format(cls.dbpath))

    @classmethod
    def load_data(cls):
        """
        Implement this function in a subclass to load data
        for your tests into the database.
        """

        pass

    def setUp(self):
        """
        Restore database from clean version.
        Delete lobs.
        """

        shutil.copy("{0}.clean".format(self.dbpath), self.dbpath)
        lobdir = os.path.join(TEST_DIR, "lob")
        if os.path.exists(lobdir):
            shutil.rmtree(lobdir)

    def save_report(self, filename):
        """
        Save report located in sample_reports directory
        with `filename`.
        """

        path = os.path.join("sample_reports", filename)

        with open(path) as file:
            report = json.load(file)

        ureport.validate(report)

        mtime = datetime.datetime.utcfromtimestamp(os.stat(path).st_mtime)
        ureport.save(self.db, report, timestamp=mtime)

        self.db.session.flush()

    def call_action(self, action_name, args_dict=None):
        """
        Run `action_name` action using `args_dict`
        as arguments.

        Returns exit code of the action

        Captures stdout and stderr during action execution
        and stores both as `self.action_stdout` and `self.action_stderr`.
        """

        p = CmdlineParser(toplevel=True)
        action_args = [action_name]

        if args_dict:
            for opt, val in args_dict.items():
                if not opt.isupper():
                    # don't spit --ARG for positional arguments
                    action_args.append("--{0}".format(opt))
                if val:
                    action_args.append("{0}".format(val))

        ns = p.parse_args(args=action_args)

        with captured_output() as (cap_stdout, cap_stderr):
            ret = ns.func(ns, self.db)

        self.action_stdout = cap_stdout.getvalue()
        self.action_stderr = cap_stderr.getvalue()

        if ret is None:
            ret = 0

        if not isinstance(ret, int):
            ret = 1

        return ret

    def compare_symbols(self, expected):
        """
        Compare symbols present in database with `expected` list.

        Used to test if retracing works as expected.
        """

        sources = self.db.session.query(SymbolSource).all()
        retraced = []
        for source in sources:
            retraced.append((source.symbol.name,
                             source.path,
                             source.line_number))

        self.assertEqual(retraced, expected)

    def tearDown(self):
        """
        Close database.
        """

        self.db.close()


class RealworldCase(DatabaseCase):
    """
    Class that provides database with real-world
    fixtures loaded.
    """

    @classmethod
    def load_data(cls):
        """
        Load real-world fixtures into the database.
        """

        meta = storage.GenericTable.metadata
        gen = fixtures.Generator(cls.db, meta)
        gen.run(realworld=True, cache=True)


class FixturesCase(DatabaseCase):
    """
    Class that provides database with generated
    fixtures.
    """

    @classmethod
    def load_data(cls):
        """
        Load fixtures into the database.
        """

        meta = storage.GenericTable.metadata
        gen = fixtures.Generator(cls.db, meta)
        gen.run(dummy=True)


class CmdLine(object):

    """
    Wrapper to access dict with attributes
    """

    def __init__(self, d):
        if d is None:
            d = {}
        self._data = d

    def __getattr__(self, name):
        if name[0] == '_':
            super(CmdLine, self).__getattr__(name)
        else:
            if name in self._data:
                return self._data[name]
            else:
                return None

    def __setattr__(self, name, value):
        if name[0] == '_':
            super(CmdLine, self).__setattr__(name, value)
        else:
            raise Exception("Command line should be read-only.")
