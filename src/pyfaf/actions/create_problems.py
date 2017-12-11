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

from operator import itemgetter
from collections import defaultdict
import satyr
from pyfaf.actions import Action
from pyfaf.problemtypes import problemtypes
from pyfaf.queries import (get_problems,
                           get_problem_component,
                           get_empty_problems,
                           get_report_by_id,
                           get_reports_by_type,
                           remove_problem_from_low_count_reports_by_type,
                           get_reports_for_problems,
                           get_unassigned_reports,
                           get_problem_by_id)
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
        empty_problems = get_empty_problems(db)
        self.log_info("Found {0} empty problems".format(len(empty_problems)))
        for db_problem in empty_problems:
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
        # The result
        thread_map = {}

        # Functions that appear in biggest number threads come last
        funcs_by_use = sorted(func_thread_map.keys(),
                              key=lambda fname: len(func_thread_map[fname]))
        for func_name in funcs_by_use:
            # Set of sets of already processed threads in which this function appears
            thread_sets = HashableSet()
            # For temporary storage for newly appearing threads
            detached_threads = HashableSet()
            # For every thread in which this function appears
            for thread in func_thread_map[func_name]:
                # If thread doesn't have its cluster assigned
                if thread not in thread_map:
                    # Add to temporary storage
                    detached_threads.add(thread)
                    continue

                # Get thread set and make sure it's in the thread_sets
                thread_set = thread_map[thread]
                if thread_set in thread_sets:
                    continue

                thread_sets.add(thread_set)

            # Assing clusters to not yet processed threads
            if 1 <= len(detached_threads) <= max_cluster_size:
                for thread in detached_threads:
                    thread_map[thread] = detached_threads

                thread_sets.add(detached_threads)

            # Biggest thread sets last
            thread_sets = sorted(thread_sets, key=len)
            cluster = set()
            # For each thread set in which this function appeared
            for thread_set in thread_sets:
                # If thread set too big by itself, skip
                if len(thread_set) > max_cluster_size:
                    break
                # If thread set cannot fit to current cluster, create a new one
                # Later thread sets are guaranteed to not fit as well, because
                # they're greater or equal in size
                new_cluster = thread_set | cluster
                if len(new_cluster) > max_cluster_size:
                    # Current cluster finished, save results
                    for thread in cluster:
                        thread_map[thread] = cluster
                    cluster = set()
                    continue
                # If thread set can fit, add to current cluster
                cluster = new_cluster

            # Save results for the last cluster
            for thread in cluster:
                thread_map[thread] = cluster

        return thread_map

    def _create_clusters(self, threads, max_cluster_size):
        self.log_debug("Creating clusters")
        func_thread_map = self._get_func_thread_map(threads)

        # Filter out unique threads
        for func_name, func_threads in func_thread_map.items():
            if len(func_threads) <= 1:
                func_thread_map.pop(func_name)

        thread_map = self._get_thread_map(func_thread_map, max_cluster_size)

        clusters = []
        processed = set()
        # Only unique and longer than 1 clusters are returned
        for threads in thread_map.itervalues():
            if threads in processed or len(threads) < 2:
                continue

            clusters.append(list(threads))
            processed.add(threads)

        return clusters

    def _find_problem_matches(self, db_problems, db_reports):
        """
        Returns a list of possible matches between old problems and a new one.
        The list items are tuples in the form `(match_metric, db_reports, db_problem)`
        Higher `match_metric` means better match.
        """
        matches = []
        for db_problem in db_problems:
            match = sum(1 for db_report in db_reports
                        if db_report in db_problem.reports)

            if match > 0:
                # Ratio of problems matched
                match_metric = float(match)/len(db_reports)
                self.log_debug("Found possible match #{0} ({1:.2f})"
                               .format(db_problem.id, match_metric))
                matches.append((match_metric, db_reports, db_problem))

        return matches

    def _iter_problems(self, db, problems, db_problems, problems_dict,
                       reuse_problems):
        """
        Yields (problem, db_problem, reports_changed) tuples.
        """
        # Three phases, see below

        # Counts for statistics
        i = 0
        lookedup_count = 0
        found_count = 0
        created_count = 0
        # List of problems left for the second phase
        second_pass = list()
        # List of possible matches for the second phase
        match_list = list()
        # Set of db_problems that were used in on of the phases. A db_problem
        # must be yielded at most once.
        db_problems_used = set()
        # Phase one: try to look up precise matches
        for problem in problems:
            i += 1

            self.log_debug("[{0} / {1}] Processing cluster"
                           .format(i, len(problems)))

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
                matches = self._find_problem_matches(db_problems, problem)
                if len(matches) == 0:
                    # No possible match found, must be a new problem
                    db_problem = Problem()
                    db.session.add(db_problem)
                    created_count += 1
                else:
                    # Leave the problems for the second phase
                    match_list += matches
                    second_pass.append(problem)
                    continue

            db_problems_used.add(db_problem)
            yield (problem, db_problem, reports_changed)

        # Phase two: yield problems in order of best match
        self.log_debug("Matching existing problems")
        self.log_debug("{0} possible matches".format(len(match_list)))
        for match_metric, problem, db_problem in sorted(match_list,
                                                        key=itemgetter(0),
                                                        reverse=True):
            if problem not in second_pass:
                self.log_debug("Already matched")
                continue
            if db_problem in db_problems_used:
                self.log_debug("Problem already used")
                continue
            found_count += 1
            second_pass.remove(problem)
            db_problems_used.add(db_problem)
            self.log_debug("Found existing problem #{0} ({1:.2f})"
                           .format(db_problem.id, match_metric))
            yield (problem, db_problem, True)

        # Phase three: create new problems if no match was found above
        self.log_debug("Processing {0} leftover problems"
                       .format(len(second_pass)))
        for problem in second_pass:
            self.log_debug("Creating problem")
            db_problem = Problem()
            db.session.add(db_problem)
            created_count += 1
            yield (problem, db_problem, True)

        self.log_debug("Total: {0}  Looked up: {1}  Found: {2}  Created: {3}"
                       .format(i, lookedup_count, found_count, created_count))

    def _create_problems(self, db, problemplugin,
                         report_min_count=0, speedup=False):
        if speedup:
            db_reports = get_reports_for_problems(db, problemplugin.name)
            db_reports += get_unassigned_reports(db, problemplugin.name,
                                                 min_count=report_min_count)
        else:
            db_reports = get_reports_by_type(db, problemplugin.name,
                                             min_count=report_min_count)
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

        invalid_report_ids_to_clean = []
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
                    if db_report.problem_id is not None:
                        invalid_report_ids_to_clean.append(db_report.id)
                else:
                    _satyr_reports.append(_satyr_report)
                    report_map[_satyr_report] = db_report

                db.session.expire(db_report)

            self.log_debug("Clustering")
            clusters = self._create_clusters(_satyr_reports, 2000)
            # Threads that share no function with another thread
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

            # Unique threads form their own unique problems
            for thread in unique_func_threads:
                problems.append(set([report_map[thread]]))

        self.log_info("Creating problems from clusters")
        if speedup:
            for problem in problems:
                if len(problem) <= 0:
                    continue
                first_report = next(iter(problem))
                if len(problem) > 1:
                    # Find assigned report
                    origin_report = None
                    for db_report in problem:
                        if db_report.problem_id:
                            origin_report = db_report

                    # Problem created only from new reports
                    comps = {}
                    if not origin_report:
                        new = Problem()
                        db.session.add(new)
                        db.session.flush()
                        first_occurrence = first_report.first_occurrence
                        last_occurrence = first_report.last_occurrence
                        for rep in problem:
                            rep.problem_id = new.id

                            if first_occurrence > rep.first_occurrence:
                                first_occurrence = rep.first_occurrence
                            if last_occurrence < rep.last_occurrence:
                                last_occurrence = rep.last_occurrence

                            if rep.component not in comps:
                                comps[rep.component] = 0

                            comps[rep.component] += 1
                        self.update_comps(db, comps, new)
                        new.last_occurrence = last_occurrence
                        new.first_occurrence = first_occurrence

                    else:
                        first_occurrence = origin_report.first_occurrence
                        last_occurrence = origin_report.last_occurrence
                        for rep in problem:
                            if not rep.problem_id:
                                rep.problem_id = origin_report.problem_id

                                if first_occurrence > rep.first_occurrence:
                                    first_occurrence = rep.first_occurrence
                                if last_occurrence < rep.last_occurrence:
                                    last_occurrence = rep.last_occurrence

                                if rep.component not in comps:
                                    comps[rep.component] = 0

                                comps[rep.component] += 1
                        orig_p = get_problem_by_id(db, origin_report.problem_id)
                        self.update_comps(db, comps, orig_p)
                        orig_p.last_occurrence = last_occurrence
                        orig_p.first_occurrence = first_occurrence
                else:
                    # The report is assigned
                    if first_report.problem_id:
                        continue
                    else:
                        # One report that wasn't matched with anything else
                        new = Problem()
                        new.first_occurrence = first_report.first_occurrence
                        new.last_occurrence = first_report.last_occurrence
                        db.session.add(new)
                        db.session.flush()

                        self.update_comps(db, {first_report.component: 1}, new)
                        first_report.problem_id = new.id
            db.session.flush()

        else:
            for problem, db_problem, reports_changed in self._iter_problems(
                    db, problems, db_problems, problems_dict, reuse_problems):

                comps = {}

                problem_last_occurrence = None
                problem_first_occurrence = None
                for db_report in problem:
                    db_report.problem = db_problem

                    if (problem_last_occurrence is None or
                            problem_last_occurrence < db_report.last_occurrence):
                        problem_last_occurrence = db_report.last_occurrence

                    if (problem_first_occurrence is None or
                            problem_first_occurrence > db_report.first_occurrence):
                        problem_first_occurrence = db_report.first_occurrence

                    if db_report.component not in comps:
                        comps[db_report.component] = 0

                    comps[db_report.component] += 1

                # In case nothing changed, we don't want to mark db_problem
                # dirty which would cause another UPDATE
                if db_problem.first_occurrence != problem_first_occurrence:
                    db_problem.first_occurrence = problem_first_occurrence
                if db_problem.last_occurrence != problem_last_occurrence:
                    db_problem.last_occurrence = problem_last_occurrence

                if reports_changed:
                    self.update_comps(db, comps, db_problem)

            self.log_debug("Removing {0} invalid reports from problems"
                           .format(len(invalid_report_ids_to_clean)))
            for report_id in invalid_report_ids_to_clean:
                db_report = get_report_by_id(db, report_id)
                if db_report is not None:
                    db_report.problem_id = None
                    db.session.add(db_report)

            if report_min_count > 0:
                self.log_debug("Removing problems from low count reports")
                remove_problem_from_low_count_reports_by_type(db,
                                                              problemplugin.name,
                                                              min_count=report_min_count)

            self.log_debug("Flushing session")
            db.session.flush()

    def update_comps(self, db, comps, db_problem):
        db_comps = sorted(comps,
                          key=lambda x: comps[x],
                          reverse=True)

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

            self._create_problems(db,
                                  problemplugin,
                                  cmdline.report_min_count,
                                  cmdline.speedup)

        self._remove_empty_problems(db)

    def tweak_cmdline_parser(self, parser):
        parser.add_problemtype(multiple=True)
        parser.add_argument("--report-min-count", type=int,
                            default=-1,
                            help="Ignore reports with count less than this.")
        parser.add_argument("--speedup", action="store_true",
                            help="Only attach new reports to existing problems")
