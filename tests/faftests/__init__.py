import os
import sys
import json
import shutil
import tempfile
import datetime
import unittest2 as unittest

pyfaf_path = os.path.join(os.path.abspath(".."), "src")
sys.path.insert(0, pyfaf_path)
os.environ["PATH"] = "{0}:{1}".format(pyfaf_path, os.environ["PATH"])

from pyfaf import config, storage, ureport
from pyfaf.storage import fixtures
from pyfaf.storage.symbol import SymbolSource


class TestCase(unittest.TestCase):
    """
    Base class for faf tests
    """

    pass


class ConfigurationCase(unittest.TestCase):
    """
    Class that initializes required configuration variables.
    """

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="faf-test-dir")

        config.config["hub.debug"] = "True"
        config.config["hub.admins"] = "admin@example.org"
        config.config["hub.serverurl"] = "https://example.org"
        config.config["hub.serveremail"] = "server@example.org"
        config.config["hub.dir"] = cls.temp_dir
        config.config["hub.urlprefix"] = ""
        config.config["main.templatesdir"] = os.path.abspath(
            "../config/templates")

        cls.dbpath = os.path.join(cls.temp_dir, "sqlite.db")
        cls.lobpath = os.path.join(cls.temp_dir, "lobs")

        cstring = "sqlite:///{0}".format(cls.dbpath)
        config.config["storage.connectstring"] = cstring
        config.config["storage.lobdir"] = cls.lobpath

    @classmethod
    def tearDownClass(cls):
        """
        Remove temporary directory.
        """

        shutil.rmtree(cls.temp_dir)


class DatabaseCase(ConfigurationCase):
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
        """

        shutil.copy("{0}.clean".format(self.dbpath), self.dbpath)

    def save_report(self, filename):
        """
        Save report located in sample_reports directory
        with `filename`.
        """

        path = os.path.join("sample_reports", filename)

        with open(path) as f:
            report = ureport.convert_to_str(json.loads(f.read()))

        report = ureport.validate(report)

        mtime = datetime.datetime.utcfromtimestamp(os.stat(path).st_mtime)
        ureport.add_report(report, self.db, utctime=mtime)

        self.db.session.flush()

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
