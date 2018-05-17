# Copyright (C) 2013  ABRT Team
# Copyright (C) 2013  Red Hat, Inc.
#
# This file is part of faf.
#
# faf is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# faf is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with faf.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import time
import math
import random
import urllib2
import tarfile
import itertools

from datetime import datetime, timedelta

import pyfaf
from pyfaf import config
from pyfaf.rpm import store_rpm_deps

from pyfaf.storage.opsys import (Arch,
                                 OpSys,
                                 OpSysRelease,
                                 OpSysComponent,
                                 OpSysReleaseComponent,
                                 Package,
                                 Build)

from pyfaf.storage.report import (Report,
                                  ReportArch,
                                  ReportBz,
                                  ReportOpSysRelease,
                                  ReportUptime,
                                  ReportBtHash,
                                  ReportBtFrame,
                                  ReportPackage,
                                  ReportBacktrace,
                                  ReportSelinuxMode,
                                  ReportHistoryDaily,
                                  ReportHistoryWeekly,
                                  ReportHistoryMonthly)

from pyfaf.storage.symbol import (Symbol,
                                  SymbolSource)

from pyfaf.storage.bugzilla import (BzUser, BzBug)

from pyfaf.storage.fixtures import data
from pyfaf.storage.fixtures import randutils

def fuzzy_timedelta(years=0, months=0):
    return timedelta(days=(years * 12 + months) * 30)


class Generator(object):
    def __init__(self, db, metadata):
        self.db = db
        self.ses = db.session
        self.meta = metadata

        self.blacklist = []

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
        print('Generating %s' % objstr)
        self.start_time = time.time()
        self.new = []

    def commit(self):
        elapsed = time.time() - self.start_time
        self.total_secs += elapsed
        print('-> Done [%.2fs]' %  elapsed)
        self.start_time = time.time()
        num_objs = len(self.new)
        self.total_objs += num_objs
        print('Adding %d objects' % num_objs)
        self.ses.add_all(self.new)
        self.ses.flush()
        self.ses.commit()
        elapsed = time.time() - self.start_time
        self.total_secs += elapsed
        print('-> Done [%.2fs]' %  elapsed)

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
    def get_occurrence_date(start, end):
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
                                            releasedate=rel[1],
                                            status='ACTIVE'))

            opsysobj.releases = relobjs
            self.add(opsysobj)
        self.commit()

    def opsyscomponents(self):
        self.begin('Components')
        opsysobjs = self.ses.query(OpSys).all()

        for comp in data.COMPS.keys():
            for obj in opsysobjs:
                if randutils.tosslow():
                    continue
                compobj = OpSysComponent(name=comp)
                compobj.opsys = obj
                for release in randutils.pickmost(obj.releases):
                    release_assoc = OpSysReleaseComponent()
                    release_assoc.release = release
                    compobj.opsysreleases.append(release_assoc)
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

    def builds(self, count=10):
        self.begin('Builds')

        comps = self.ses.query(OpSysComponent).all()

        for comp in comps:
            for i in range(count):
                new = Build()
                new.component = comp
                new.epoch = 0
                new.version = '{0}.{1}'.format(random.randrange(0, 5),
                                               random.randrange(0, 20))
                new.release = random.randrange(0, 100)
                self.add(new)

        self.commit()

    def packages(self):
        self.begin('Packages')

        arches = self.ses.query(Arch).all()

        for build in self.ses.query(Build):
            for package_name in data.COMPS[build.component.name]['packages']:
                new = Package()
                new.arch = random.choice(arches)
                new.build = build
                new.name = package_name
                self.add(new)

        self.commit()

    def bz_users(self, count=1):
        self.begin('Bz users')
        for i in range(count):
            new = BzUser()
            new.email = 'bzuser@example.org'
            new.name = 'Example'
            new.real_name = 'Sample user'
            new.can_login = True
            self.add(new)

        self.commit()

    def bz_bugs(self, count=100):
        comps = self.ses.query(OpSysComponent).all()
        releases = self.ses.query(OpSysRelease).all()
        bz_users = self.ses.query(BzUser).all()

        self.begin('Bz bugs')
        for i in range(count):
            comp = random.choice(comps)
            bug = BzBug()
            bug.id = 900000 + i*1337 # over 9000
            bug.summary = '[faf] Crash in component {0}'.format(comp)


            bug.status = random.choice(pyfaf.storage.bugzilla.BUG_STATES)
            if bug.status == 'CLOSED':
                bug.resolution = random.choice(
                    pyfaf.storage.bugzilla.BUG_RESOLUTIONS)

            when = datetime.now().date() + fuzzy_timedelta(
                months=random.randrange(-6, 0))

            bug.creation_time = when
            bug.last_change_time = when
            bug.opsysrelease = random.choice(releases)
            bug.component = comp
            bug.creator = random.choice(bz_users)
            bug.whiteboard = 'empty'
            self.add(bug)

        self.commit()

    def reports(self, count=100):
        comps = self.ses.query(OpSysComponent).all()
        releases = self.ses.query(OpSysRelease).all()
        arches = self.ses.query(Arch).all()
        symbols = self.ses.query(SymbolSource).all()
        packages = self.ses.query(Package).all()
        bugs = self.ses.query(BzBug).all()

        for rel in releases:
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
                occ_date = self.get_occurrence_date(since, till)
                if occ_date > datetime.now():
                    # skipping reports from the future
                    continue
                report.first_occurrence = report.last_occurrence = occ_date
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

                report_bt.crashfn = btframe.symbolsource.symbol.name

                current = []
                last_occ = occ_date
                crashed_pkgs = random.sample(packages, random.randrange(1, 4))
                related_pkgs = random.sample(packages, random.randrange(1, 4))

                for j in range(report.count):
                    if j > 1:
                        occ_date = self.get_occurrence_date(since, till)
                        if occ_date > datetime.now():
                            continue

                    if occ_date > last_occ:
                        last_occ = occ_date

                    arch = random.choice(arches)
                    day = occ_date.date()
                    week = day - timedelta(days=day.weekday())
                    month = day.replace(day=1)
                    smode = random.choice(['DISABLED', 'PERMISSIVE', 'ENFORCING'])

                    stat_map = [(ReportArch, [('arch', arch)]),
                                (ReportOpSysRelease, [('opsysrelease', rel)]),
                                (ReportHistoryMonthly, [('opsysrelease', rel),
                                                        ('month', month)]),
                                (ReportHistoryWeekly, [('opsysrelease', rel),
                                                       ('week', week)]),
                                (ReportHistoryDaily, [('opsysrelease', rel),
                                                      ('day', day)]),
                                (ReportSelinuxMode, [('mode', smode)]),
                               ]

                    # add crashed and related packages
                    for typ in ['CRASHED', 'RELATED']:
                        for pkg in locals()['{0}_pkgs'.format(typ.lower())]:
                            if randutils.toss():
                                stat_map.append(
                                    (ReportPackage,
                                     [('installed_package', pkg),
                                      ('running_package', pkg),
                                      ('type', typ)])
                                    )

                    if randutils.tosshigh():
                        stat_map.append((ReportUptime, [('uptime_exp',
                                                         int(math.log(random.randrange(1, 100000))))]))

                    if randutils.toss():
                        stat_map.append((ReportOpSysRelease,
                                         [('opsysrelease', random.choice(releases))]))

                    if randutils.tosslow():
                        stat_map.append((ReportBz,
                                         [('bzbug', random.choice(bugs))]))

                    for table, cols in stat_map:
                        fn = lambda x: isinstance(x, table)
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
                report.last_occurrence = last_occ
            self.commit()

    def from_sql_file(self, fname):
        fname += '.sql'
        print('Loading %s' % fname)
        fixture_topdir = os.path.dirname(os.path.realpath(__file__))

        if not os.path.isfile(os.path.join(fixture_topdir, 'sql', fname)):
            fixture_topdir = '/usr/share/faf/fixtures'

        with open(os.path.join(fixture_topdir, 'sql', fname)) as file:
            for line in file.readlines():
                self.ses.execute(line)

        self.ses.commit()

    def restore_package_deps(self):
        print('Restoring package dependencies from rpms')
        for package in self.ses.query(Package):
            store_rpm_deps(self.db, package)

        self.ses.commit()

    def restore_lob_dir(self, url=None, cache=True):
        print('Restoring lob dir from remote archive')

        if url is None:
            fixture_topdir = os.path.dirname(os.path.realpath(__file__))
            fname = 'lob_download_location'

            if not os.path.isfile(os.path.join(fixture_topdir, fname)):
                fixture_topdir = '/usr/share/faf/fixtures'

            with open(os.path.join(fixture_topdir, fname)) as file:
                url = file.readlines()[0].strip()


        cname = os.path.basename(url)
        cpath = os.path.join('/tmp', cname)
        if cache:
            if os.path.isfile(cpath):
                try:
                    print('Using {0}'.format(cpath))
                    tar = tarfile.open(cpath, mode='r').extractall(
                        path=config.CONFIG["storage.lobdir"])

                    print('Lob dir restored successfuly from cache')
                    return
                except tarfile.TarError as ex:
                    print('Unable to extract archive: {0}'.format(str(ex)))

        print('Using: {0}'.format(url))
        try:
            rem = urllib2.urlopen(url, cpath)
            total_size = rem.info().getheader('Content-Length').strip()
            total_size = int(total_size)
            chunk_size = 1 << 17
            bytes_so_far = 0
            with open(cpath, 'wb') as f:
                while 1:
                    chunk = rem.read(chunk_size)

                    if not chunk:
                        break

                    bytes_so_far += len(chunk)
                    f.write(chunk)

                    percent = float(bytes_so_far) / total_size
                    percent = round(percent*100, 2)
                    sys.stdout.write("Downloaded %d of %d bytes (%0.2f%%)\r" %
                                     (bytes_so_far, total_size, percent))

                    if bytes_so_far >= total_size:
                        sys.stdout.write('\n')

            tar = tarfile.open(cpath, mode='r').extractall(
                path=config.CONFIG["storage.lobdir"])
        except urllib2.URLError as ex:
            print('Unable to download archive: {0}'.format(str(ex)))
        except tarfile.TarError as ex:
            print('Unable to extract archive: {0}'.format(str(ex)))

        print('Lob dir restored successfuly')

        if not cache:
            os.unlink(cpath)

    def run(self, dummy=False, realworld=False, url=None, cache=True):

        if dummy:
            self.arches()
            self.opsysreleases()
            self.opsyscomponents()
            self.symbols()
            self.builds()
            self.packages()
            self.bz_users()
            self.bz_bugs()
            self.reports()

            print('All Done, added %d objects in %.2f seconds' % (
                self.total_objs, self.total_secs))

        if realworld:
            self.from_sql_file('archs')
            self.from_sql_file('opsys')
            self.from_sql_file('opsysreleases')
            self.from_sql_file('opsyscomponents')
            self.from_sql_file('opsysreleasescomponents')
            self.from_sql_file('buildsys')

            self.from_sql_file('builds')
            self.from_sql_file('buildarchs')

            self.from_sql_file('packages')

            self.from_sql_file('tags')
            self.from_sql_file('archstags')
            self.from_sql_file('buildstags')
            self.from_sql_file('taginheritances')

            self.restore_lob_dir(url, cache)

            self.restore_package_deps()

            print('All Done')
