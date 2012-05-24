import time
import math
import random
import itertools

from datetime import datetime, timedelta

from pyfaf.storage.opsys import (Arch,
                                 OpSys,
                                 OpSysRelease,
                                 OpSysComponent)

from pyfaf.storage.report import (Report,
                                  ReportArch,
                                  ReportOpSysRelease,
                                  ReportExecutable,
                                  ReportUptime,
                                  ReportBtHash,
                                  ReportBtFrame,
                                  ReportPackage,
                                  ReportUnknownPackage,
                                  ReportReason,
                                  ReportBacktrace,
                                  ReportSelinuxMode,
                                  ReportSelinuxContext,
                                  ReportHistoryDaily,
                                  ReportHistoryWeekly,
                                  ReportHistoryMonthly,
                                  ReportKernelTaintState)

from pyfaf.storage.symbol import (Symbol,
                                  SymbolSource)

from pyfaf.storage.fixtures import data
from pyfaf.storage.fixtures import randutils

def fuzzy_timedelta(years=0, months=0):
    return timedelta(days=(years * 12 + months) * 30)


class Generator(object):
    def __init__(self, db, metadata):
        self.db = db
        self.ses = db.session
        self.meta = metadata

        self.blacklist = ['_dbmd',]

        self.new = []
        self.total_objs = 0
        self.total_secs = 0

    def introspect_meta(self):
        for table in self.meta.sorted_tables:
            if table.name in self.blacklist:
                continue
            yield table

    def add(self, obj):
        self.new.append(obj)

    def extend(self, objs):
        self.new.extend(objs)

    def begin(self, objstr):
        print 'Generating %s' % objstr
        self.start_time = time.time()
        self.new = []

    def commit(self):
        elapsed = time.time() - self.start_time
        self.total_secs += elapsed
        print '-> Done [%.2fs]' %  elapsed
        self.start_time = time.time()
        num_objs = len(self.new)
        self.total_objs += num_objs
        print 'Adding %d objects' % num_objs
        self.ses.add_all(self.new)
        self.ses.flush()
        elapsed = time.time() - self.start_time
        self.total_secs += elapsed
        print '-> Done [%.2fs]' %  elapsed

    @staticmethod
    def get_release_end_date(since, opsys):
        vary = random.randrange(-1, 2)

        restd = fuzzy_timedelta(months=6+vary)
        if opsys == 'RHEL':
            restd = fuzzy_timedelta(years=2+vary, months=2+vary)

        if opsys == 'openSUSE':
            restd = fuzzy_timedelta(months=10+vary)

        return since + restd

    @staticmethod
    def get_occurence_date(start, end):
        rand = random.gammavariate(2, 0.2)
        stime = time.mktime(start.timetuple())
        etime = time.mktime(end.timetuple())
        new = stime + (etime - stime) * rand
        return datetime.fromtimestamp(new)

    def arches(self):
        self.begin('Arches')
        for arch in data.ARCH:
            self.add(Arch(name=arch))
        self.commit()

    def opsysreleases(self):
        self.begin('Releases')
        for opsysname, releases in data.OPSYS.items():
            opsysobj = OpSys(name=opsysname)
            relobjs = []
            for rel in releases:
                relobjs.append(OpSysRelease(version=rel[0],
                    releasedate=rel[1]))

            opsysobj.releases = relobjs
            self.add(opsysobj)
        self.commit()

    def opsyscomponents(self):
        self.begin('Components')
        opsysobjs = self.ses.query(OpSys).all()

        for comp in data.COMPS:
            for obj in opsysobjs:
                if randutils.tosslow():
                    continue
                compobj = OpSysComponent(name=comp)
                compobj.opsys = obj
                compobj.opsysreleases = randutils.pickmost(obj.releases)
                self.add(compobj)
        self.commit()

    def symbols(self):
        self.begin('Symbols')
        for fun, lib in itertools.product(data.FUNS, data.LIBS):
            symbolsource = SymbolSource()
            symbolsource.build_id = random.randrange(1, 100)
            symbolsource.line_number = random.randrange(1, 100)
            symbolsource.source_path = '/usr/lib64/python2.7/%s.py' % lib
            symbolsource.path = '/usr/lib64/python2.7/%s.pyo' % lib
            symbolsource.hash = randutils.randhash()
            symbolsource.offset = randutils.randhash()

            symbol = Symbol()
            symbol.name = fun
            symbol.normalized_path = lib
            self.add(symbol)

            symbolsource.symbol = symbol
            self.add(symbolsource)

        self.commit()

    def reports(self, count=100):
        comps = self.ses.query(OpSysComponent).all()
        releases = self.ses.query(OpSysRelease).all()
        arches = self.ses.query(Arch).all()
        symbols = self.ses.query(SymbolSource).all()

        for rel in self.ses.query(OpSysRelease).all():
            self.begin('Reports for %s %s' % (rel.opsys.name, rel.version))
            since = rel.releasedate
            if since is None:
                since = datetime.now().date() + fuzzy_timedelta(
                    months=random.randrange(-6, 0))
            till = self.get_release_end_date(since, rel.opsys)

            for i in range(count):
                report = Report()
                report.type = 'USERSPACE'
                report.count = random.randrange(1, 20)
                occ_date = self.get_occurence_date(since, till)
                if occ_date > datetime.now():
                    # skipping reports from the future
                    continue
                report.first_occurence = report.last_occurence = occ_date
                report.component = random.choice(comps)
                self.add(report)

                report_bt = ReportBacktrace()
                report_bt.report = report
                self.add(report_bt)

                bthash = ReportBtHash()
                bthash.type = 'NAMES'
                bthash.hash = randutils.randhash()
                bthash.backtrace = report_bt
                self.add(bthash)

                for j in range(random.randrange(1, 40)):
                    btframe = ReportBtFrame()
                    btframe.backtrace = report_bt
                    btframe.order = j
                    btframe.symbolsource = random.choice(symbols)

                current = []
                last_occ = occ_date
                for j in range(report.count):
                    if j > 1:
                        occ_date = self.get_occurence_date(since, till)
                        if occ_date > datetime.now():
                            continue

                    if occ_date > last_occ:
                        last_occ = occ_date

                    arch = random.choice(arches)
                    day = occ_date.date()
                    week = day - timedelta(days=day.weekday())
                    month = day.replace(day=1)
                    stat_map = [(ReportArch, [('arch', arch)]),
                                (ReportOpSysRelease, [('opsysrelease', rel)]),
                                (ReportHistoryMonthly, [('opsysrelease', rel),
                                    ('month', month)]),
                                (ReportHistoryWeekly, [('opsysrelease', rel),
                                    ('week', week)]),
                                (ReportHistoryDaily, [('opsysrelease', rel),
                                    ('day', day)])]

                    if randutils.tosshigh():
                        stat_map.append((ReportUptime, [('uptime_exp',
                            int(math.log(random.randrange(1, 100000))))]))

                    for table, cols in stat_map:
                        fn = lambda x: type(x) == table
                        for report_stat in filter(fn, current):
                            matching = True
                            for name, value in cols:
                                if getattr(report_stat, name) != value:
                                    matching = False
                            if matching:
                                report_stat.count += 1
                                break
                        else:
                            report_stat = table()
                            report_stat.report = report
                            for name, value in cols:
                                setattr(report_stat, name, value)
                            report_stat.count = 1
                            current.append(report_stat)

                self.extend(current)
                report.last_occurence = last_occ
            self.commit()

    def run(self):
        self.arches()
        self.opsysreleases()
        self.opsyscomponents()
        self.symbols()
        self.reports()

        print 'All Done, added %d objects in %.2f seconds' % (self.total_objs,
            self.total_secs)
