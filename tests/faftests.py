import os
import json
import shutil
import tempfile
import datetime
import unittest2 as unittest

from pyfaf import config, storage, ureport
from pyfaf.storage import fixtures
from pyfaf.storage.symbol import SymbolSource

class DatabaseCase(unittest.TestCase):
    '''
    Class that provides initialized faf database for the tests.
    '''
    @classmethod
    def setUpClass(cls):
        '''
        Set up sqlite database in a temp directory.
        Databse created in this step is restored
        for each test.
        '''
        cls.temp_dir = tempfile.mkdtemp(prefix="faf-test-retrace")
        cls.dbpath = os.path.join(cls.temp_dir, 'sqlite.db')
        cls.lobpath = os.path.join(cls.temp_dir, 'lobs')

        config.CONFIG["storage.connectstring"] = 'sqlite:///{0}'.format(cls.dbpath)
        config.CONFIG["storage.lobdir"] = cls.lobpath

        cls.db = storage.Database(session_kwargs={
                                    'autoflush': False,
                                    'autocommit': False})
        cls.load_data()

        shutil.copy(cls.dbpath, '{0}.clean'.format(cls.dbpath))

    @classmethod
    def load_data(cls):
        '''
        Implement this function in a subclass to load data
        for your tests into the database.
        '''
        pass

    @classmethod
    def tearDownClass(cls):
        '''
        Remove temporary database.
        '''
        shutil.rmtree(cls.temp_dir)

    def setUp(self):
        '''
        Restore database from clean version.
        '''
        shutil.copy('{0}.clean'.format(self.dbpath), self.dbpath)

    def save_report(self, filename):
        '''
        Save report located in sample_reports directory
        with `filename`.
        '''
        path = os.path.join('sample_reports', filename)

        with open(path) as f:
            report = ureport.convert_to_str(json.loads(f.read()))

        report = ureport.validate(report)

        mtime = datetime.datetime.utcfromtimestamp(os.stat(path).st_mtime)
        ureport.add_report(report, self.db, utctime=mtime)

        self.db.session.flush()

    def compare_symbols(self, expected):
        '''
        Compare symbols present in database with `expected` list.

        Used to test if retracing works as expected.
        '''
        sources = self.db.session.query(SymbolSource).all()
        retraced = []
        for source in sources:
            retraced.append((source.symbol.name, source.path, source.line_number))

        self.assertEqual(retraced, expected)

    def tearDown(self):
        '''
        Close database.
        '''
        self.db.close()

class RealworldCase(DatabaseCase):
    '''
    Class that provides database with real-world
    fixtures loaded.
    '''
    @classmethod
    def load_data(cls):
        '''
        Load real-world fixtures into the database.
        '''
        meta = storage.GenericTable.metadata
        gen = fixtures.Generator(cls.db, meta)
        gen.run(realworld=True, cache=True)

class FixturesCase(DatabaseCase):
    '''
    Class that provides database with generated
    fixtures.
    '''
    @classmethod
    def load_data(cls):
        '''
        Load fixtures into the database.
        '''
        meta = storage.GenericTable.metadata
        gen = fixtures.Generator(cls.db, meta)
        gen.run(dummy=True)
