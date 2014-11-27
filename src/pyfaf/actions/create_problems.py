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

import satyr
from collections import defaultdict
from pyfaf.actions import Action
from pyfaf.problemtypes import problemtypes
from pyfaf.queries import (get_problems,
                           get_problem_component,
                           get_empty_problems,
                           get_reports_by_type)
from pyfaf.storage import Problem, ProblemComponent, Report


class HashableSet(set):
    """
    A standard set object that hashes under its memory address.
    This is a single-purpose class just to test presence of the set
    in another set and should not be used anywhere else.
    """

    def __hash__(self):
        return id(self)

    def __str__(self):
        return super(HashableSet, self).__str__()

    def __repr__(self):
        return super(HashableSet, self).__repr__()


class CreateProblems(Action):
    name = "create-problems"

    def __init__(self):
        super(CreateProblems, self).__init__()

    def _remove_empty_problems(self, db):
        self.log_info("Removing empty problems")
        for db_problem in get_empty_problems(db):
            self.log_debug("Removing empty problem #{0}"
                           .format(db_problem.id))
            db.session.delete(db_problem)
        db.session.flush()

    def _get_func_thread_map(self, threads):
        self.log_debug("Creating mapping function name -> threads")
        result = {}

        for thread in threads:
            for frame in thread.frames:
                if frame.function_name == "??":
                    continue

                result.setdefault(frame.function_name, set()).add(thread)

        return result

    def _get_thread_map(self, func_thread_map, max_cluster_size):
        self.log_debug("Creating mapping thread -> similar threads")
        thread_map = {}

        funcs_by_use = sorted(func_thread_map.keys(),
                              key=lambda fname: len(func_thread_map[fname]))

        for func_name in funcs_by_use:
            thread_sets = HashableSet()
            detached_threads = HashableSet()
            for thread in func_thread_map[func_name]:
                if thread not in thread_map:
                    detached_threads.add(thread)
                    continue

                thread_set = thread_map[thread]
                if thread_set in thread_sets:
                    continue

                thread_sets.add(thread_set)

            if 1 <= len(detached_threads) <= max_cluster_size:
                for thread in detached_threads:
                    thread_map[thread] = detached_threads

                thread_sets.add(detached_threads)

            thread_sets = sorted(thread_sets, key=len)

            group_sets = [[]]
            size = 0

            for thread_set in thread_sets:
                if len(thread_set) > max_cluster_size:
                    break

                if size + len(thread_set) > max_cluster_size:
                    group_sets.append([thread_set])
                    size = len(thread_set)
                    break

                group_sets[-1].append(thread_set)
                size += len(thread_set)

            for join_sets in group_sets:
                if len(join_sets) < 2:
                    continue

                new_threads = join_sets[-1]
                for threads in join_sets[:-1]:
                    new_threads |= threads

                for thread in new_threads:
                    thread_map[thread] = new_threads

        return thread_map

    def _create_clusters(self, threads, max_cluster_size):
        self.log_debug("Creating clusters")
        func_thread_map = self._get_func_thread_map(threads)

        for func_name, func_threads in func_thread_map.items():
            if len(func_threads) <= 1:
                func_thread_map.pop(func_name)

        thread_map = self._get_thread_map(func_thread_map, max_cluster_size)

        clusters = []
        processed = set()
        for threads in thread_map.itervalues():
            if threads in processed or len(threads) < 2:
                continue

            clusters.append(list(threads))
            processed.add(threads)

        return clusters

    def _find_problem(self, db_problems, db_reports):
        for db_problem in db_problems:
            match = sum(1 for db_report in db_reports
                        if db_report in db_problem.reports)

            if match > len(db_problem.reports) / 2:
                self.log_debug("Reusing problem #{0}".format(db_problem.id))
                return db_problem

        return None

    def _create_problems(self, db, problemplugin):
        db_reports = get_reports_by_type(db, problemplugin.name)
        db_problems = get_problems(db)

        # dict to get db_problem by problem_id
        self.log_debug("Creating problem reuse dict")
        problems_dict = {}
        for db_problem in db_problems:
            problems_dict[db_problem.id] = db_problem
        # dict to get report_ids by problem_id
        problem_report = defaultdict(list)
        for db_report in db_reports:
            if db_report.problem_id is not None:
                problem_report[db_report.problem_id].append(db_report.id)
        # create lookup dict for problems
        reuse_problems = {}
        for (problem_id, report_ids) in problem_report.items():
            reuse_problems[tuple(sorted(report_ids))] = problem_id

        problems = []
        if len(db_reports) < 1:
            self.log_info("No reports found")
        elif len(db_reports) == 1:
            db_report = db_reports[0]
            if db_report.problem is None:
                problems.append([db_report])
        else:
            report_map = {}
            _satyr_reports = []
            i = 0
            for db_report in db_reports:
                i += 1
                self.log_debug("[{0} / {1}] Loading report #{2}"
                               .format(i, len(db_reports), db_report.id))

                _satyr_report = problemplugin._db_report_to_satyr(db_report)
                if _satyr_report is None:
                    self.log_debug("Unable to create satyr report")
                else:
                    _satyr_reports.append(_satyr_report)
                    report_map[_satyr_report] = db_report

                db.session.expire(db_report)

            self.log_debug("Clustering")
            clusters = self._create_clusters(_satyr_reports, 2000)
            unique_func_threads = set(_satyr_reports) - set().union(*clusters)

            dendrograms = []
            i = 0
            for cluster in clusters:
                i += 1
                self.log_debug("[{0} / {1}] Computing distances"
                               .format(i, len(clusters)))
                distances = satyr.Distances(cluster, len(cluster))

                self.log_debug("Getting dendrogram")
                dendrograms.append(satyr.Dendrogram(distances))

            for dendrogram, cluster in zip(dendrograms, clusters):
                problem = []
                for dups in dendrogram.cut(0.3, 1):
                    reports = set(report_map[cluster[dup]] for dup in dups)
                    problem.append(reports)

                problems.extend(problem)

            for thread in unique_func_threads:
                problems.append(set([report_map[thread]]))

        self.log_info("Creating problems")
        i = 0
        lookedup_count = 0
        found_count = 0
        created_count = 0
        for problem in problems:
            i += 1

            self.log_debug("[{0} / {1}] Creating problem"
                           .format(i, len(problems)))
            comps = {}

            reports_changed = True
            problem_id = reuse_problems.get(
                tuple(sorted([db_report.id for db_report in problem])), None)
            if problem_id is not None:
                db_problem = problems_dict.get(problem_id, None)
                reports_changed = False
                lookedup_count += 1
                self.log_debug("Looked up existing problem #{0}"
                               .format(db_problem.id))
            else:
                db_problem = self._find_problem(db_problems, problem)
                found_count += 1

            if db_problem is None:
                db_problem = Problem()
                db.session.add(db_problem)

                db_problems.append(db_problem)
                created_count += 1

            for db_report in problem:
                db_report.problem = db_problem

                if (db_problem.last_occurrence is None or
                    db_problem.last_occurrence < db_report.last_occurrence):
                    db_problem.last_occurrence = db_report.last_occurrence

                if (db_problem.first_occurrence is None or
                    db_problem.first_occurrence < db_report.first_occurrence):
                    db_problem.first_occurrence = db_report.first_occurrence

                if db_report.component not in comps:
                    comps[db_report.component] = 0

                comps[db_report.component] += 1

            if reports_changed:
                db_comps = sorted(comps, key=lambda x: comps[x], reverse=True)

                order = 0
                for db_component in db_comps:
                    order += 1

                    db_pcomp = get_problem_component(db, db_problem, db_component)
                    if db_pcomp is None:
                        db_pcomp = ProblemComponent()
                        db_pcomp.problem = db_problem
                        db_pcomp.component = db_component
                        db_pcomp.order = order
                        db.session.add(db_pcomp)

        self.log_debug("Total: {0}  Looked up: {1}  Found: {2}  Created: {3}"
                       .format(i, lookedup_count, found_count, created_count))
        self.log_debug("Flushing session")
        db.session.flush()

    def run(self, cmdline, db):
        if len(cmdline.problemtype) < 1:
            ptypes = problemtypes.keys()
        else:
            ptypes = cmdline.problemtype

        i = 0
        for ptype in ptypes:
            i += 1
            problemplugin = problemtypes[ptype]
            self.log_info("[{0} / {1}] Processing problem type: {2}"
                          .format(i, len(ptypes), problemplugin.nice_name))

            self._create_problems(db, problemplugin)

        self._remove_empty_problems(db)

    def tweak_cmdline_parser(self, parser):
        parser.add_problemtype(multiple=True)
