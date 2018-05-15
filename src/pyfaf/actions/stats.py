# -*- coding: utf-8 -*-
# Copyright (C) 2014  ABRT Team
# Copyright (C) 2014  Red Hat, Inc.
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

from __future__ import unicode_literals

from __future__ import division
import datetime
import collections

from sqlalchemy import func

from pyfaf.actions import Action
from pyfaf.queries import (get_release_ids,
                           query_hot_problems,
                           query_longterm_problems,
                           get_history_target,
                           get_history_sum,
                           get_report_count_by_component,
                           get_report_stats_by_component,
                           get_crashed_unknown_package_nevr_for_report,
                           get_crashed_package_for_report)

from pyfaf.storage.opsys import OpSysComponent
from pyfaf.storage.report import Report
from pyfaf.utils.date import prev_days
from pyfaf.utils.web import webfaf_installed, reverse
from pyfaf.utils.parse import cmp_evr
from pyfaf.problemtypes import problemtypes


class Stats(Action):
    name = "stats"

    def __init__(self):
        super(Stats, self).__init__()

        self.history_type = "daily"
        self.graph_symbols = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        self.comps_filter = ["will-crash"]

    def components(self, cmdline, db, opsys, release):
        """
        Get statistics for most crashing components
        """

        hist_table, hist_field = get_history_target(self.history_type)
        total = get_history_sum(db, opsys, release)
        comps = get_report_count_by_component(db, opsys, release)

        if cmdline.last:
            now = datetime.datetime.now()
            since = now - datetime.timedelta(days=int(cmdline.last))
            comps = comps.filter(hist_field >= since)
            total = total.filter(hist_field >= since)

        total_num = total.first()[0]

        limit = int(cmdline.count)
        limit_details = int(cmdline.detail_count)
        results = []

        for num, (comp, count) in enumerate(comps):
            if num >= limit:
                break

            if comp in self.comps_filter:
                continue

            reports = get_report_stats_by_component(db, comp, opsys,
                                                    release,
                                                    self.history_type)

            if cmdline.last:
                reports = reports.filter(hist_field >= since)

            problem_ids = set()
            attached_reports = []

            for report, report_count in reports:
                if len(problem_ids) >= limit_details:
                    break
                if not report.problem:
                    continue
                if report.problem.id in problem_ids:
                    continue
                if report.quality < 0 and not cmdline.include_low_quality:
                    continue

                problem_ids.add(report.problem.id)

                problem_url = ""
                if webfaf_installed():
                    problem_url = reverse("problems.item",
                                          problem_id=report.problem.id)

                attached_reports.append((problem_url, report.bugs))

            results.append((comp, count, attached_reports))

        if not results:
            return ""

        out = "Components:\n\n"

        for num, (comp, count, reports) in enumerate(results):
            if reports:
                out += ("{0}. {1} seen {2} times ({3:.0%} of all reports)\n"
                        .format(num + 1, comp, count, count / float(total_num)))

                for problem_url, bugs in reports:
                    if problem_url or bugs:
                        out += "    {0} {1}\n".format(
                            problem_url, ", ".join(map(str, bugs)))

        return out

    def trends(self, cmdline, db, opsys, release):
        """
        Get trends for crashing components
        """

        hist_table, hist_field = get_history_target(self.history_type)

        num_days = 7
        if cmdline.last:
            num_days = int(cmdline.last)

        last_date = datetime.date.today() - datetime.timedelta(days=num_days)

        comp_detail = []

        comps = get_report_count_by_component(db, opsys, release)
        comps = comps.filter(hist_field >= last_date)

        for (comp, count) in comps:
            if comp.name in self.comps_filter:
                continue

            report_ids = (db.session.query(Report.id)
                          .join(OpSysComponent)
                          .filter(OpSysComponent.id == comp.id)).subquery()

            history = (db.session.query(hist_field,
                                        func.sum(hist_table.count)
                                        .label("count"))
                       .filter(hist_table.report_id.in_(report_ids))
                       .filter(hist_field >= last_date)
                       .filter(hist_field < datetime.date.today())
                       .group_by(hist_field)
                       .order_by(hist_field).all())

            if len(history) < 2:
                continue

            hist_dict = collections.defaultdict(int)
            for key, value in history:
                hist_dict[key] = value

            # Compute linear regression
            xsum, ysum, xysum, xxsum, yysum = 0., 0., 0., 0., 0.
            for x, day in enumerate(prev_days(num_days)):
                y = hist_dict[day]
                xsum += x
                ysum += y
                xysum += x * y
                xxsum += x * x
                yysum += y * y

            # y = bx + a
            b = xysum - xsum * ysum // num_days
            b //= xxsum - xsum ** 2 // num_days

            a = ysum - b * xsum
            a //= num_days

            first_day = hist_dict[prev_days(num_days)[0]]
            last_day = hist_dict[prev_days(num_days)[-1]]

            Comp = collections.namedtuple("Component", "name jump a b history")
            comp_tuple = Comp(
                name=comp.name,
                jump=last_day - first_day,
                a=a,
                b=b,
                history=hist_dict)

            comp_detail.append(comp_tuple)

        trend_data = sorted(comp_detail, key=lambda x: x.b, reverse=True)

        if not trend_data:
            return ""

        # render trend data
        render_fn = self._trends_render
        if cmdline.graph:
            render_fn = self._trends_render_with_graph

        out = "Most destabilized components:\n\n"
        out += render_fn(trend_data, cmdline.count, num_days)
        out += "\n"

        out += "Most stabilized components:\n\n"
        trend_data.reverse()
        out += render_fn(trend_data, cmdline.count, num_days)
        out += "\n"

        return out

    def _trends_render_with_graph(self, collection, num, num_days):
        """
        Render trend data with UTF8 graphs
        """

        row = "{component:<40} {jump:>7}   {graph:>" + str(num_days) + "}"
        txt = row.format(component="Component", jump="Jump", graph="Graph")
        out = txt + "\n"
        out += "-" * len(txt) + "\n"

        for comp in collection[:num]:
            counts = []
            for day in prev_days(num_days):
                counts.append(comp.history[day])

            minval = min(counts)
            maxval = max(counts)
            scale = ((maxval - minval) << 8) // (len(self.graph_symbols) - 1)
            scale = max(scale, 1)
            graph = ""

            for day in prev_days(num_days):
                graph += self.graph_symbols[((comp.history[day] - minval)
                                             << 8) // scale]

            out += row.format(component=comp.name,
                              jump=comp.jump,
                              a=comp.a,
                              b=comp.b,
                              graph=graph.replace(" ", "") + "\n\n")

        return out

    def _trends_render(self, collection, num, num_days):
        """
        Render trend data
        """

        row = "{component:<40} {jump:>7}"
        txt = row.format(component="Component", jump="Jump")
        out = txt + "\n"
        out += "-" * len(txt) + "\n"

        for comp in collection[:num]:
            out += row.format(component=comp.name,
                              jump=comp.jump) + "\n"

        return out

    def problems(self, cmdline, db, opsys, release):
        """
        Get hot/long-term problem statistics
        """

        release_ids = get_release_ids(db, opsys, release)

        num_days = 7
        if cmdline.last:
            num_days = int(cmdline.last)

        since = datetime.datetime.now() - datetime.timedelta(days=num_days)

        hot = query_hot_problems(db, release_ids, history=self.history_type,
                                 last_date=since)

        if not cmdline.include_low_quality:
            hot = [x for x in hot if x.quality >= 0]
        hot = [p for p in hot if p.type in self.ptypes]

        out = ""
        if hot:
            out += "Hot problems:\n\n"
            out += self._render_problems(hot, cmdline.count, release_ids)
            out += "\n"
            if webfaf_installed():
                out += "URL: "
                out += reverse("problems.dashboard")
                out += "\n\n"

        lt = query_longterm_problems(db, release_ids, history=self.history_type)
        if not cmdline.include_low_quality:
            lt = [x for x in lt if x.quality >= 0]
        lt = [p for p in lt if p.type in self.ptypes]

        if lt:
            out += "Long-term problems:\n\n"
            out += self._render_problems(lt, cmdline.count, release_ids)
            out += "\n\n"

        return out

    def _render_problems(self, problems, num, release_ids):
        """
        Render hot/long-term problem data
        """

        # calculate width of components column
        comp_field_size = 35
        for problem in problems[:num]:
            components = ', '.join(problem.unique_component_names)
            if len(components) > comp_field_size:
                comp_field_size = len(components)

        row = ('{id:<10} {components:<' +
               str(comp_field_size + 3) +
               '} {count:>5} ' +
               '{probable_fix:<15}\n')

        txt = row.format(id='ID', components='Components', count='Count',
                         probable_fix='Probably fixed')
        txt += '-' * (len(txt) - 1) + '\n'

        for problem in problems[:num]:
            txt += row.format(
                id=problem.id,
                components=', '.join(problem.unique_component_names),
                count=problem.count,
                probable_fix=problem.probable_fix_for_opsysrelease_ids(
                    release_ids))

        return txt

    def text_overview(self, cmdline, db, opsys, release):
        release_ids = get_release_ids(db, opsys, release)

        num_days = 7
        if cmdline.last:
            num_days = int(cmdline.last)

        since = datetime.datetime.now() - datetime.timedelta(days=num_days)

        hot = query_hot_problems(db, release_ids, history=self.history_type,
                                 last_date=since)

        if not cmdline.include_low_quality:
            hot = [x for x in hot if x.quality >= 0]

        ptypes = ""
        if len(self.ptypes) != len(problemtypes):
            ptypes = " "+", ".join(self.ptypes)
        out = "Overview of the top {0}{1} crashes over the last {2} days:\n".format(
            cmdline.count, ptypes, num_days)

        hot = [p for p in hot if p.type in self.ptypes]

        for (rank, problem) in enumerate(hot[:cmdline.count]):
            out += "#{0} {1} - {2}x\n".format(
                rank+1,
                ', '.join(problem.unique_component_names),
                problem.count)

            # Reports with bugzillas for this OpSysRelease go first
            reports = sorted(problem.reports,
                             cmp=lambda x, y: len([b for b in x.bugs if b.opsysrelease_id in release_ids])
                             - len([b for b in y.bugs if b.opsysrelease_id in release_ids]), reverse=True)

            if webfaf_installed():
                for report in reports[:3]:
                    out += "{0}\n".format(reverse("reports.bthash_forward",
                                                  bthash=report.hashes[0].hash))
                    for bug in report.bugs:
                        out += "  {0}\n".format(bug.url)
            else:
                for report in reports[:3]:
                    out += "Report BT hash: {0}\n".format(report.hashes[0].hash)
            if len(problem.reports) > 3:
                out += "... and {0} more.\n".format(len(problem.reports)-3)

            if problem.tainted:
                out += "Kernel tainted.\n"

            crash_function = problem.crash_function
            if crash_function:
                out += "Crash function: {0}\n".format(crash_function)

            affected_all = []
            for report in problem.reports:
                affected_known = [
                    (affected.build.base_package_name,
                     affected.build.epoch,
                     affected.build.version,
                     affected.build.release) for affected in
                    get_crashed_package_for_report(db, report.id)]

                affected_unknown = \
                    get_crashed_unknown_package_nevr_for_report(db, report.id)

                affected_all += affected_known + affected_unknown
            affected_all = sorted(set(affected_all),
                                  cmp=lambda a, b: cmp_evr(a[1:], b[1:]),
                                  reverse=True)

            if affected_all:
                out += "Affected builds: {0}".format(", ".join(
                    ["{0}-{1}:{2}-{3}".format(n, e, v, r)
                     for (n, e, v, r) in affected_all[:5]]))
                if len(problem.reports) > 5:
                    out += " and {0} more.".format(len(problem.reports)-5)
                out += "\n"

            pfix = problem.probable_fix_for_opsysrelease_ids(release_ids)
            if len(pfix) > 0:
                out += ("Problem seems to be fixed since the release of {0}\n"
                        .format(pfix))
            out += "\n"

        return out

    def run(self, cmdline, db):
        opsys = self.get_opsys_name(cmdline.opsys)
        release = cmdline.opsys_release

        if len(cmdline.problemtype) < 1:
            self.ptypes = list(problemtypes.keys())
        else:
            self.ptypes = cmdline.problemtype

        out = ""

        if cmdline.components:
            out += self.components(cmdline, db, opsys, release)
            out += "\n\n"

        if cmdline.problems:
            out += self.problems(cmdline, db, opsys, release)
            out += "\n"

        if cmdline.trends:
            out += self.trends(cmdline, db, opsys, release)

        if cmdline.text_overview:
            out += self.text_overview(cmdline, db, opsys, release)

        print(out.rstrip())

    def tweak_cmdline_parser(self, parser):
        parser.add_opsys(required=True)
        parser.add_opsys_release(required=True)
        parser.add_argument("--components", action="store_true", default=False,
                            help="get most crashing components")
        parser.add_argument("--trends", action="store_true", default=False,
                            help="get trends for crashing components")
        parser.add_argument("--problems", action="store_true", default=False,
                            help="show hot/longterm problem statistics")
        parser.add_argument("--text-overview", action="store_true", default=False,
                            help="show text overview of hot problems")
        parser.add_argument("--last", metavar="N", help="use last N days")
        parser.add_argument("--count", help="show this number of items",
                            default=5, type=int)
        parser.add_argument("--detail-count",
                            help="show this number of items for each component",
                            default=2, type=int)
        parser.add_argument("--include-low-quality", action="store_true",
                            help="include low quality reports",
                            default=False)
        parser.add_argument("--graph", help="Use inline graphs for trends",
                            action="store_true", default=False)
        parser.add_problemtype(multiple=True)
