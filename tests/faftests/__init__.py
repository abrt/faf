import os
import sys
import json
import shutil
import datetime
import unittest

import psycopg2
import testing.postgresql

cpath = os.path.dirname(os.path.realpath(__file__))
# alter path so we can import pyfaf
pyfaf_path = os.path.abspath(os.path.join(cpath, "../..", "src"))
sys.path.insert(1, pyfaf_path)
os.environ["PATH"] = "{0}:{1}".format(pyfaf_path, os.environ["PATH"])

# use separate config file for tests
os.environ["FAF_CONFIG_FILE"] = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "test_config.conf")

# create temporary directory for the tests
TEST_DIR = "/tmp/faf_test_data"


from pyfaf import storage, ureport, config
from pyfaf.cmdline import CmdlineParser
from pyfaf.actions.init import Init
from pyfaf.utils.contextmanager import captured_output
from pyfaf.storage import fixtures
from pyfaf.storage.symbol import SymbolSource

class TestCase(unittest.TestCase):
    """
    Class that initializes required configuration variables.
    """
    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_DIR):
            shutil.rmtree(TEST_DIR)
        os.makedirs(TEST_DIR)

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
        Database created in this step is restored
        for each test.
        """

        super(DatabaseCase, cls).setUpClass()

        cls.pgdir = os.path.join(TEST_DIR, "pg")

        cls.postgresql = testing.postgresql.Postgresql(
            base_dir=cls.pgdir)

        # load semver extension
        conn = psycopg2.connect(**cls.postgresql.dsn())
        conn.set_isolation_level(0)
        cur = conn.cursor()
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS semver;")
        except:
            # older PostgreSQL doesn't support CREATE EXTENSION
            # load semver type manually

            with open("/usr/share/pgsql/contrib/semver.sql") as f:
                sql = f.read()
                cur.execute(sql)

        conn.close()

        _set_up_db_conf(cls.postgresql)

        cls.dbpath = os.path.join(cls.pgdir, "data")
        cls.clean_dbpath = os.path.join(TEST_DIR, "pg_clean_data")

        cls.reports_path = os.path.abspath(
            os.path.join(cpath, "..", "sample_reports"))

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

        if not os.path.isdir(self.clean_dbpath):
            # no .clean version, load data and save .clean
            self.prepare()
            # required due to mixing of sqlalchemy and flask-sqlalchemy
            # fixed in flask-sqlalchemy >= 2.0
            self.db.session._model_changes = {}
            self.db.session.commit()
            self.db.close()
            shutil.copytree(self.dbpath, self.clean_dbpath)

        self.postgresql.stop()
        shutil.rmtree(self.pgdir)
        self.postgresql = testing.postgresql.Postgresql(
            base_dir=self.pgdir,
            copy_data_from=self.clean_dbpath)

        _set_up_db_conf(self.postgresql)

        # reinit DB with new version
        storage.Database.__instance__ = None
        self.db = storage.Database(session_kwargs={
            "autoflush": False,
            "autocommit": False})

        # required due to mixing of sqlalchemy and flask-sqlalchemy
        # fixed in flask-sqlalchemy >= 2.0
        self.db.session._model_changes = {}

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
            arch = storage.Arch(name=arch_name)
            self.db.session.add(arch)
            setattr(self, "arch_{0}".format(arch_name), arch)

        centos_sys = storage.OpSys(name="CentOS")
        self.db.session.add(centos_sys)

        self.opsys_centos = centos_sys

        releases = []
        versions = ["6.7", "6.8", "7.1", "7.2", "7.3", "7.7"]
        for ver in versions:
            rel = storage.OpSysRelease(opsys=centos_sys, version=ver, status="ACTIVE")

            releases.append(rel)
            self.db.session.add(rel)
            setattr(self, "release_{0}".format(ver), rel)

        sys = storage.OpSys(name="Fedora")
        self.db.session.add(sys)

        self.opsys_fedora = sys

        releases = []
        for ver in range(17, 21):
            rel = storage.OpSysRelease(opsys=sys, version=ver, status="ACTIVE")
            releases.append(rel)
            self.db.session.add(rel)
            setattr(self, "release_{0}".format(ver), rel)

        for cname in ["faf", "systemd", "kernel", "ibus-table", "eclipse",
                      "will-crash", "ibus-table-ruby", "xorg-x11-drv-nouveau"]:

            comp = storage.OpSysComponent(opsys=sys, name=cname)
            self.db.session.add(comp)

            comp = storage.OpSysComponent(opsys=centos_sys, name=cname)
            self.db.session.add(comp)

            setattr(self, "comp_{0}".format(cname), comp)

            for rel in releases:
                rcomp = storage.OpSysReleaseComponent(release=rel, component=comp)
                self.db.session.add(rcomp)

        if flush:
            self.db.session.flush()

    def save_report_dict(self, report):
        ureport.validate(report)

        mtime = datetime.datetime.utcnow()
        ureport.save(self.db, report, timestamp=mtime)

        self.db.session.flush()

    def load_report(self, filename):
        path = os.path.join(self.reports_path, filename)

        with open(path) as file:
            report = json.load(file)

        return report

    def save_report(self, filename):
        """
        Save report located in sample_reports directory
        with `filename`.
        """

        self.save_report_dict(self.load_report(filename))

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

    def call_action_ordered_args(self, action_name, args_list=None):
        """
        Run `action_name` action using `args_list`
        as arguments.

        Returns exit code of the action

        Captures stdout and stderr during action execution
        and stores both as `self.action_stdout` and `self.action_stderr`.
        This is different from call_action by that, that arguments are in the
            same order passed to the actual method
        """

        p = CmdlineParser(toplevel=True)
        action_args = [action_name] + args_list

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
        self.postgresql.stop()
        self.db._del()

    def create_user(self, usrnum=''):
        """
        Create a new fake user.
        """
        user = storage.User(mail='faker{}@localhost'.format(usrnum),
                            username='faker{}'.format(usrnum),
                            privileged=True,
                            admin=True)
        self.db.session.add(user)

    def create_report(self, rid):
        """
        Create a new fake report.
        """
        report = storage.Report(id=rid,
                                type="type",
                                count=2,
                                component=self.comp_faf)
        self.db.session.add(report)

    def create_problem(self):
        """
        Create a new fake problem.
        """
        problem = storage.Problem()
        self.db.session.add(problem)

    def create_bugzilla_user(self, bzuid):
        """
        Create a new fake bugzilla user with id='bzuid'.
        """
        user = storage.BzUser(id=bzuid,
                              email='faker{}@localhost'.format(bzuid),
                              name='faker{}@localhost'.format(bzuid),
                              real_name='Fake Bugzilla User',
                              can_login=False)
        self.db.session.add(user)

    def create_bugzilla(self, bugid, bzuid):
        """
        Create fake Bugzilla with comments, attachments, history and ccs.
        """
        timenow = datetime.datetime.now()
        tracker = storage.Bugtracker(name="Fakezilla")
        self.db.session.add(tracker)

        bzbug = storage.BzBug(id=bugid,
                              summary='Fake bugzilla summary',
                              status='CLOSED',
                              resolution='NOTABUG',
                              creation_time=timenow,
                              last_change_time=timenow,
                              private=False,
                              tracker_id=1,
                              opsysrelease_id=1,
                              component_id=1,
                              whiteboard='fake white board',
                              creator_id=bzuid)
        self.db.session.add(bzbug)

        bzattach = storage.BzAttachment(id=bugid,
                                        bug_id=bugid,
                                        user_id=bzuid,
                                        mimetype='text/plain',
                                        description='fake json text',
                                        creation_time=timenow,
                                        last_change_time=timenow,
                                        is_private=False,
                                        is_patch=False,
                                        is_obsolete=False,
                                        filename='fake_filename.json')
        self.db.session.add(bzattach)

        bzcomment = storage.BzComment(bug_id=bugid,
                                      user_id=bzuid,
                                      number=1,
                                      creation_time=timenow,
                                      is_private=False)
        self.db.session.add(bzcomment)

        bzcomment1 = storage.BzComment(bug_id=bugid,
                                       user_id=bzuid,
                                       number=2,
                                       creation_time=timenow,
                                       is_private=False,
                                       attachment_id=bugid)
        self.db.session.add(bzcomment1)

        bzbughist = storage.BzBugHistory(bug_id=bugid,
                                         user_id=bzuid,
                                         time=timenow,
                                         field='status',
                                         added='POST',
                                         removed='NEW')
        self.db.session.add(bzbughist)

        bzbugcc = storage.BzBugCc(bug_id=bugid, user_id=bzuid)

        self.db.session.add(bzbugcc)

    def create_contact_email_report(self, emailid, usruid=''):
        """
        Create ContactEmail and link it with a Report in ReportContactMail table.
        """
        mail = storage.ContactEmail(id=emailid,
                                    email_address='faker{}@localhost'.format(usruid))
        self.db.session.add(mail)

        report = (self.db.session.query(storage.Report)
                  .filter(storage.Report.id == emailid)
                  .first())

        rcmail = storage.ReportContactEmail(report_id=emailid,
                                            contact_email_id=emailid)
        self.db.session.add(rcmail)


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


def _set_up_db_conf(pg_obj):
    params = pg_obj.dsn()
    config.config["storage.dbuser"] = params["user"]
    config.config["storage.dbpasswd"] = ""
    config.config["storage.dbhost"] = params["host"]
    config.config["storage.dbport"] = params["port"]
    config.config["storage.dbname"] = params["database"]
