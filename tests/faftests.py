import os
import json
import shutil
import tempfile
import datetime
import unittest2 as unittest

from pyfaf import config, storage, ureport
from pyfaf.storage import fixtures
from pyfaf.storage.symbol import SymbolSource

class RealworldCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="faf-test-retrace")
        cls.dbpath = os.path.join(cls.temp_dir, 'sqlite.db')
        cls.lobpath = os.path.join(cls.temp_dir, 'lobs')

        config.CONFIG["storage.connectstring"] = 'sqlite:///{0}'.format(cls.dbpath)
        config.CONFIG["storage.lobdir"] = cls.lobpath

        cls.db = storage.Database(session_kwargs={
                                    'autoflush': False,
                                    'autocommit': False})

        meta = storage.GenericTable.metadata
        gen = fixtures.Generator(cls.db, meta)
        gen.run(realworld=True, cache=True)
        shutil.copy(cls.dbpath, '{0}.clean'.format(cls.dbpath))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir)

    def setUp(self):
        shutil.copy('{0}.clean'.format(self.dbpath), self.dbpath)

    def save_report(self, filename):
        path = os.path.join('sample_reports', filename)

        with open(path) as f:
            report = ureport.convert_to_str(json.loads(f.read()))

        report = ureport.validate(report)

        mtime = datetime.datetime.utcfromtimestamp(os.stat(path).st_mtime)
        ureport.add_report(report, self.db, utctime=mtime)

        self.db.session.flush()

    def compare_symbols(self, expected):
        sources = self.db.session.query(SymbolSource).all()
        retraced = []
        for source in sources:
            retraced.append((source.symbol.name, source.path, source.line_number))

        self.assertEqual(retraced, expected)

    def tearDown(self):
        self.db.close()

