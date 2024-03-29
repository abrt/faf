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

from typing import Dict, Generator, List, Optional, Set, Tuple

from operator import itemgetter
from collections import defaultdict
from concurrent.futures import as_completed, ThreadPoolExecutor

import satyr

from pyfaf.actions import Action
from pyfaf.problemtypes import problemtypes
from pyfaf.queries import (get_problems,
                           get_problem_component,
                           get_empty_problems,
                           unassign_reports,
                           get_reports_by_type,
                           remove_problem_from_low_count_reports_by_type,
                           get_reports_for_problems,
                           get_unassigned_reports,
                           get_problem_by_id)
from pyfaf.storage import Problem, ProblemComponent, Report, ReportBtThread


class HashableSet(set):
    """
    A standard set object that hashes under its memory address.
    This is a single-purpose class just to test presence of the set
    in another set and should not be used anywhere else.
    """

    def __hash__(self) -> int:
        return id(self)


class CreateProblems(Action):
    name = "create-problems"

    def __init__(self) -> None:
        super().__init__()
        self._max_workers = 4

    def _remove_empty_problems(self, db) -> None:
        self.log_info("Removing empty problems")
        empty_problems = get_empty_problems(db)
        self.log_info("Found {0} empty problems".format(len(empty_problems)))
        for db_problem in empty_problems:
            self.log_debug("Removing empty problem #%d", db_problem.id)
            db.session.delete(db_problem)
        db.session.flush()

    def _get_func_thread_map(self, threads) -> Dict[str, Set[ReportBtThread]]:
        self.log_debug("Creating mapping function name -> threads")
        result = {}

        for thread in threads:
            for frame in thread.frames:
                if frame.function_name == "??":
                    continue

                result.setdefault(frame.function_name, set()).add(thread)

        return result

    def _get_thread_map(self, func_thread_map, max_cluster_size) -> Dict[ReportBtThread, Set[ReportBtThread]]:
        self.log_debug("Creating mapping thread -> similar threads")
        # The result
        thread_map = {}

        # Functions that appear in biggest number threads come last
        funcs_by_use = sorted(func_thread_map.keys(),
                              key=lambda fname: len(func_thread_map[fname]))
        for func_name in funcs_by_use:
            # Set of sets of already processed threads in which this function appears
            thread_sets = set()
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
                thread_set = frozenset(thread_map[thread])
                if thread_set in thread_sets:
                    continue

                thread_sets.add(thread_set)

            # Assign clusters to not yet processed threads
            if 1 <= len(detached_threads) <= max_cluster_size:
                thread_map.update({thread: detached_threads for thread in detached_threads})
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
            thread_map.update({thread: cluster for thread in cluster})

        return thread_map

    def _create_clusters(self, threads, max_cluster_size) -> List[List[ReportBtThread]]:
        self.log_debug("Creating clusters")
        func_thread_map = self._get_func_thread_map(threads)

        # Filter out unique threads
        for func_name, func_threads in func_thread_map.copy().items():
            if len(func_threads) <= 1:
                func_thread_map.pop(func_name)

        thread_map = self._get_thread_map(func_thread_map, max_cluster_size)

        clusters = []
        processed = set()
        # Only unique and longer than 1 clusters are returned
        for threads_ in thread_map.values():
            if threads_ in processed or len(threads_) < 2:
                continue

            clusters.append(list(threads_))
            processed.add(frozenset(threads_))

        return clusters

    def _find_problem_matches(self, db_problems, db_reports) -> List[Tuple[float, List[Report], Problem]]:
        """
        Returns a list of possible matches between old problems and a new one.
        The list items are tuples in the form `(match_metric, db_reports, db_problem)`
        Higher `match_metric` means better match.
        """

        def _compute_match(problem_reports) -> int:
            db_problem, db_reports = problem_reports[0], problem_reports[1]

            return sum(1 for db_report in db_reports if db_report in db_problem.reports)

        matches = []
        db_reports_len = len(db_reports)
        with ThreadPoolExecutor(self._max_workers) as executor:
            futures = {
                executor.submit(_compute_match, (problem, db_reports)): problem
                for problem in db_problems
            }

            for future in as_completed(futures):
                db_problem = futures.pop(future)
                match = future.result()
                if match > 0:
                    # Ratio of problems matched
                    match_metric = float(match)/db_reports_len
                    self.log_debug("Found possible match #%d (%.2f)", db_problem.id, match_metric)
                    matches.append((match_metric, db_reports, db_problem))

        return matches

    def _iter_problems(self, db, problems, db_problems, problems_dict,
                       reuse_problems) -> Generator[Tuple[Report, Problem, Optional[bool]], None, None]:
        """
        Yields (problem, db_problem, reports_changed) tuples.
        """
        # Three phases, see below
        problems_total = len(problems)

        # Counts for statistics
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
        for i, problem in enumerate(problems, start=1):

            self.log_debug("[%d / %d] Processing cluster", i, problems_total)

            reports_changed = True
            problem_id = reuse_problems.get(
                tuple(sorted([db_report.id for db_report in problem])), None)
            if problem_id is not None:
                db_problem = problems_dict.get(problem_id, None)
                reports_changed = False
                lookedup_count += 1
                self.log_debug("Looked up existing problem #%d", db_problem.id)
            else:
                matches = self._find_problem_matches(db_problems, problem)
                if not matches:
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
        self.log_debug("%d possible matches", len(match_list))
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
        self.log_debug("Processing %d leftover problems", len(second_pass))
        for problem in second_pass:
            self.log_debug("Creating problem")
            db_problem = Problem()
            db.session.add(db_problem)
            created_count += 1
            yield (problem, db_problem, True)

        self.log_debug("Total: %d  Looked up: %d  Found: %d  Created: %d",
                       problems_total, lookedup_count, found_count, created_count)

    def _create_problems(self, db, problemplugin, #pylint: disable=too-many-statements
                         report_min_count=0, speedup=False) -> None:
        if speedup:
            self.log_debug("[%s] Getting reports for problems", problemplugin.name)
            db_reports = get_reports_for_problems(db, problemplugin.name)

            self.log_debug("[%s] Getting unassigned reports", problemplugin.name)
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
        if not db_reports:
            self.log_info("No reports found")
        elif len(db_reports) == 1:
            db_report = db_reports[0]
            if db_report.problem is None:
                problems.append([db_report])
        else:
            report_map = {}
            _satyr_reports = []
            db_reports_len = len(db_reports)
            n_processed = 1

            # split the work to multiple workers
            with ThreadPoolExecutor(self._max_workers) as executor:
                # schedule db_reports for processing
                futures = {
                    executor.submit(problemplugin.db_report_to_satyr, report): report
                    for report in db_reports
                }

                for future in as_completed(futures):
                    db_report = futures.pop(future)
                    self.log_debug("[%d / %d] Loading report #%d", n_processed, db_reports_len, db_report.id)

                    _satyr_report = future.result()
                    if _satyr_report is None:
                        self.log_debug("Unable to create satyr report")
                        if db_report.problem_id is not None:
                            invalid_report_ids_to_clean.append(db_report.id)
                    else:
                        _satyr_reports.append(_satyr_report)
                        report_map[_satyr_report] = db_report

                    n_processed += 1

                db.session.expire_all()

            self.log_debug("Clustering")
            clusters = self._create_clusters(_satyr_reports, 2000)
            # Threads that share no function with another thread
            unique_func_threads = set(_satyr_reports) - set().union(*clusters)

            dendrograms = []
            clusters_len = len(clusters)
            for i, cluster in enumerate(clusters, start=1):
                self.log_debug("[%d / %d] Computing distances", i, clusters_len)
                distances = satyr.Distances(cluster, len(cluster))

                self.log_debug("Getting dendrogram")
                dendrograms.append(satyr.Dendrogram(distances))

            dendogram_cut = 0.3
            if speedup:
                dendogram_cut = dendogram_cut * 1.1

            for dendrogram, cluster in zip(dendrograms, clusters):
                problem = []
                for dups in dendrogram.cut(dendogram_cut, 1):
                    reports = set(report_map[cluster[dup]] for dup in dups)
                    problem.append(reports)

                problems.extend(problem)

            # Unique threads form their own unique problems
            for thread in unique_func_threads:
                problems.append({report_map[thread]})

        self.log_info("Creating problems from clusters")
        if speedup:
            for problem in problems:
                if not problem:
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

            self.log_debug("Removing %d invalid reports from problems",
                           len(invalid_report_ids_to_clean))
            unassign_reports(db, invalid_report_ids_to_clean)

            if report_min_count > 0:
                self.log_debug("Removing problems from low count reports")
                remove_problem_from_low_count_reports_by_type(db,
                                                              problemplugin.name,
                                                              min_count=report_min_count)

            self.log_debug("Flushing session")
            db.session.flush()

    def update_comps(self, db, comps, db_problem) -> None:
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

    def run(self, cmdline, db) -> None:
        if not cmdline.problemtype:
            ptypes = list(problemtypes.keys())
        else:
            ptypes = cmdline.problemtype

        self._max_workers = cmdline.max_workers

        ptypes_len = len(ptypes)
        for i, ptype in enumerate(ptypes, start=1):
            problemplugin = problemtypes[ptype]
            self.log_info("[{0} / {1}] Processing problem type: {2}"
                          .format(i, ptypes_len, problemplugin.nice_name))

            self._create_problems(db,
                                  problemplugin,
                                  cmdline.report_min_count,
                                  cmdline.speedup)

        self._remove_empty_problems(db)

    def tweak_cmdline_parser(self, parser) -> None:
        parser.add_problemtype(multiple=True)
        parser.add_argument("-w", "--max-workers", type=int,
                            default=4,
                            help="Maximal number of worker threads to use during problem processing.")
        parser.add_argument("--report-min-count", type=int,
                            default=-1,
                            help="Ignore reports with count less than this.")
        parser.add_argument("--speedup", action="store_true",
                            help="Only attach new reports to existing problems")
