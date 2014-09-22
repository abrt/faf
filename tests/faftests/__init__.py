import os
import sys
import json
import shutil
import datetime
import unittest2 as unittest

cpath = os.path.dirname(os.path.realpath(__file__))
# alter path so we can import pyfaf
pyfaf_path = os.path.abspath(os.path.join(cpath, "../..", "src"))
sys.path.insert(0, pyfaf_path)
os.environ["PATH"] = "{0}:{1}".format(pyfaf_path, os.environ["PATH"])

# use separate config file for tests
os.environ["FAF_CONFIG_FILE"] = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "test_config.conf")

# create temporary directory for the tests
TEST_DIR = "/tmp/faf_test_data"
if os.path.exists(TEST_DIR):
    shutil.rmtree(TEST_DIR)
os.makedirs(TEST_DIR)


from pyfaf import storage, ureport
from pyfaf.cmdline import CmdlineParser
from pyfaf.actions.init import Init
from pyfaf.utils.contextmanager import captured_output
from pyfaf.storage import fixtures
from pyfaf.storage.symbol import SymbolSource

from pyfaf.storage.opsys import (Arch,
                                 OpSys,
                                 OpSysComponent,
                                 OpSysRelease,
                                 OpSysReleaseComponent)


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
        cls.clean_dbpath = "{0}.clean".format(cls.dbpath)

        cls.db = storage.Database(session_kwargs={
                                  "autoflush": False,
                                  "autocommit": False},
                                  create_schema=True)

    def prepare(self):
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

        if not os.path.isfile(self.clean_dbpath):
            # no .clean version, load data and save .clean
            self.prepare()
            self.db.session.commit()
            self.db.close()
            shutil.copy(self.dbpath, self.clean_dbpath)

        shutil.copy(self.clean_dbpath, self.dbpath)

        # reinit DB with new version
        storage.Database.__instance__ = None
        self.db = storage.Database(session_kwargs={
                                   "autoflush": False,
                                   "autocommit": False},
                                   create_schema=True)

        lobdir = os.path.join(TEST_DIR, "lob")
        if os.path.exists(lobdir):
            shutil.rmtree(lobdir)

    def basic_fixtures(self, flush=True):
        """
        Add Arch, OpSys, OpSysRelease and OpSysComponent fixtures

        Store as self.arch_noarch, self_opsys_fedora, self.release_19,
        self.comp_kernel, ...
        """

        for arch_name in Init.archs:
            arch = Arch(name=arch_name)
            self.db.session.add(arch)
            setattr(self, "arch_{0}".format(arch_name), arch)

        sys = OpSys(name="Fedora")
        self.db.session.add(sys)
        self.opsys_fedora = sys

        releases = []
        for ver in range(17, 21):
            rel = OpSysRelease(opsys=sys, version=ver, status="ACTIVE")
            releases.append(rel)
            self.db.session.add(rel)
            setattr(self, "release_{0}".format(ver), rel)

        for cname in ["faf", "systemd", "kernel", "ibus-table", "eclipse",
                      "will-crash"]:

            comp = OpSysComponent(opsys=sys, name=cname)
            self.db.session.add(comp)
            setattr(self, "comp_{0}".format(cname), comp)

            for rel in releases:
                rcomp = OpSysReleaseComponent(release=rel, component=comp)
                self.db.session.add(rcomp)

        if flush:
            self.db.session.flush()

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

    def prepare(self):
        """
        Load real-world fixtures into the database.
        """

        meta = storage.GenericTable.metadata
        gen = fixtures.Generator(self.db, meta)
        gen.run(realworld=True, cache=True)


class FixturesCase(DatabaseCase):
    """
    Class that provides database with generated
    fixtures.
    """

    def prepare(self):
        """
        Load fixtures into the database.
        """

        meta = storage.GenericTable.metadata
        gen = fixtures.Generator(self.db, meta)
        gen.run(dummy=True)
