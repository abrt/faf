import logging

import btparser

from sqlalchemy import func

import pyfaf
from pyfaf.storage.opsys import OpSys, OpSysComponent
from pyfaf.storage.report import Report
from pyfaf.storage.problem import Problem, ProblemComponent

def get_funs_clusters(threads, max_cluster_size, log_debug=None):
    # Return list of sets of threads clustered by common function names

    # function name -> set of threads
    funs_threads = dict()
    for thread in threads:
        for frame in thread.frames:
            name = frame.get_function_name()
            if name == "??":
                continue
            if not funs_threads.has_key(name):
                funs_threads[name] = set([thread])
            funs_threads[name].add(thread)

    if log_debug:
        log_debug("Found {0} unique function names.".format(len(funs_threads)))

    # remove functions which are only in one thread
    for (name, thread_set) in funs_threads.items():
        if len(thread_set) == 1:
            del funs_threads[name]

    if log_debug:
        log_debug("Found {0} function names used in more than one thread.".format(len(funs_threads)))

    # sort the function names by number of threads having them
    funs_by_use = list(funs_threads.keys())
    funs_by_use.sort(key = lambda name: len(funs_threads[name]))

    if log_debug:
        log_debug("10 most common function names:")
        for name in reversed(funs_by_use[-10:]):
            log_debug("- {0} {1}".format(len(funs_threads[name]), name))

    # thread -> threads
    thread_threads = dict()

    # merge threads with common funs
    for name in funs_by_use:
        thread_sets = []
        included_sets_ids = set()
        detached_threads = set()
        for thread in funs_threads[name]:
            if thread in thread_threads:
                threads = thread_threads[thread]
                if id(threads) in included_sets_ids:
                    continue
                thread_sets.append(threads)
                included_sets_ids.add(id(threads))
            else:
                detached_threads.add(thread)

        # add new set of threads which are alone now
        if 1 <= len(detached_threads) <= max_cluster_size:
            for thread in detached_threads:
                thread_threads[thread] = detached_threads
            thread_sets.append(detached_threads)

        # sort the sets by their size
        thread_sets.sort(key = lambda threads: len(threads))

        # group the sets so that the sizes of the results are not over the limit
        group_sets = [[]]
        size = 0
        for thread_set in thread_sets:
            if len(thread_set) > max_cluster_size:
                break
            if size + len(thread_set) > max_cluster_size:
                group_sets.append([thread_set])
                size = len(thread_set)
            else:
                group_sets[-1].append(thread_set)
                size += len(thread_set)

        # join the sets in the groups, smaller sets with the largest one
        for join_sets in group_sets:
            if len(join_sets) < 2:
                continue

            new_threads = set()
            for threads in join_sets[:-1]:
                assert len(threads & new_threads) == 0
                new_threads |= threads

            assert len(join_sets[-1] & new_threads) == 0
            join_sets[-1] |= new_threads

            for thread in new_threads:
                thread_threads[thread] = join_sets[-1]

    saved_sets_ids = set()
    saved_sets = []
    saved_threads = set()
    for threads in thread_threads.itervalues():
        if id(threads) in saved_sets_ids or len(threads) < 2:
            continue
        saved_sets.append(list(threads))
        saved_sets_ids.add(id(threads))
        assert len(saved_threads & threads) == 0
        saved_threads |= threads

    return saved_sets

def cluster_funs_clusters(funs_clusters, distance, log_debug=None):
    # Return list of dendrograms corresponding to the funs clusters.
    dendrograms = []

    for (i, funs_cluster) in enumerate(funs_clusters):
        if log_debug:
            log_debug("Clustering funs cluster {0}/{1} (size = {2}).".\
                    format(i + 1, len(funs_clusters), len(funs_cluster)))
        dendrograms.append(btparser.Dendrogram(
            btparser.Distances(distance, funs_cluster, len(funs_cluster))))

    return dendrograms

def get_common_components(components_lists):
    # Find the components which are in a majority of the components lists.
    components_sets = [set(l) for l in components_lists]
    all_comps = set()

    for comps in components_sets:
        all_comps |= comps

    result = set()

    # Return set of components which are in at least 80% of the sets.
    for comp in all_comps:
        x = filter(lambda comps: comp in comps, components_sets)
        if len(x) > 8 * len(components_sets) / 10:
            result.add(comp)

    return result

def get_ordered_components(common_components, components_lists):
    # Keep only common components in the lists and uniqify them.
    lists = []
    for comps in components_lists:
        l = []
        for comp in comps:
            if comp not in common_components:
                continue
            if len(l) == 0 or l[-1] != comp:
                l.append(comp)
        lists.append(l)

    # Sort the common components by average maximum index in the lists.

    for l in lists:
        l.reverse()

    comp_avg_level = []
    for comp in common_components:
        lnum = 0
        lsum = 0
        for l in lists:
            if comp not in l:
                continue
            lnum += 1
            lsum += len(l) - l.index(comp)
        comp_avg_level.append([comp, float(lsum) / lnum if lnum > 0 else 0.0])

    comp_avg_level.sort(key=lambda (comp, avg): avg, reverse=True)
    #logging.debug("Common component levels: {0}".format(comp_avg_level))

    return [comp for (comp, avg) in comp_avg_level]

def component_lists_match(components1, components2):
    for (comp1, comp2) in zip(components1, components2):
        if comp1 != comp2 and comp1 != None:
            return False
    return True

def filter_components_lists(components_lists):
    # Remove duplicates first.
    lists = []
    for l in components_lists:
        if l not in lists:
            lists.append(l)

    # Remove lists which are substrings of other list, None matches anything.
    result = []
    for l1 in lists:
        for l2 in lists:
            if len(l1) > len(l2) or l1 == l2:
                continue
            for start in xrange(len(l2) - len(l1) + 1):
                if component_lists_match(l1, l2[start:start + len(l1)]):
                    break
            else:
                continue
            break
        else:
            result.append(l1)

    return result

def get_frequent_frames(threads, rel_usage):
    # Return dict of sets of most frequently used function names
    # in the threads for each library.

    ignore = set(['main'])

    frame_counts = dict()
    for thread in threads:
        for frame in thread.frames:
            name = frame.get_function_name()
            if name == "??" or name in ignore:
                continue
            lib = frame.get_library_name()
            if lib not in frame_counts:
                frame_counts[lib] = dict()
            if name not in frame_counts[lib]:
                frame_counts[lib][name] = 0
            frame_counts[lib][name] += 1

    result = dict()

    for (lib, frames) in frame_counts.iteritems():
        sorted_counts = sorted(frames.values())
        if len(sorted_counts) < 3:
            continue
        median = sorted_counts[len(sorted_counts) / 2]
        freq_names = set(name for (name, count) in frames.iteritems() if count > median * rel_usage)

        result[lib] = freq_names

    return result

def is_frame_frequent(frame, freq_frames):
    name = frame.get_function_name()
    if name == "??":
        return False
    lib = frame.get_library_name()
    if lib not in freq_frames or name not in freq_frames[lib]:
        return False
    return True

def remove_frequent_frames(threads, freq_frames, max_frames):
    # Remove frequent frames from the threads.

    for thread in threads:
        frames = []
        for frame in thread.frames:
            if len(frames) == max_frames:
                break
            if not is_frame_frequent(frame, freq_frames):
                frames.append(frame)
        thread.frames = frames

def create_problems(db, max_cluster_size=2000, distance="levenshtein",
                    cut_level=0.3, max_fun_usage=None):

    if "processing.clusterframes" in pyfaf.config.CONFIG:
        max_frames = int(pyfaf.config.CONFIG["processing.clusterframes"])
    else:
        max_frames = 16

    current_problems = dict()
    current_report_problems = dict()
    report_ids = []
    opsys_ids = dict()
    component_names = dict()

    for report_id, problem_id, opsys_id, component_name in \
            db.session.query(Report.id, Report.problem_id, OpSysComponent.opsys_id, OpSysComponent.name).\
            join(OpSysComponent).order_by(Report.id).all():
        if problem_id not in current_problems:
            current_problems[problem_id] = set()
        current_problems[problem_id].add(report_id)
        current_report_problems[report_id] = problem_id
        report_ids.append(report_id)
        opsys_ids[report_id] = opsys_id
        component_names[report_id] = component_name

    report_threads = pyfaf.ureport.get_report_btp_threads(report_ids, db,
            max_frames=4 * max_frames if max_fun_usage else max_frames, log_debug=logging.debug)

    thread_names = dict()
    threads = []
    for report_id, thread in report_threads:
        threads.append(thread)
        thread_names[thread] = report_id

    if max_fun_usage:
        logging.info("Removing too frequent functions from threads.")
        freq_frames = pyfaf.cluster.get_frequent_frames(threads, max_fun_usage)
        pyfaf.cluster.remove_frequent_frames(threads, freq_frames, max_frames)

    logging.info("Clustering by common function names (maximum cluster size = {0}).".format(max_cluster_size))
    funs_clusters = pyfaf.cluster.get_funs_clusters(threads, max_cluster_size, log_debug=logging.debug)

    # Find threads which are not in any funs cluster (i.e. their function names are all unique).
    unique_funs_threads = set(threads) - set().union(*funs_clusters)

    # Sort threads in the funs clusters by report id to stabilize the clustering results.
    for funs_cluster in funs_clusters:
        funs_cluster.sort(key=lambda x: thread_names[x])

    logging.info("Clustering by {0} distance.".format(distance))
    dendrograms = pyfaf.cluster.cluster_funs_clusters(funs_clusters, distance, log_debug=logging.debug)

    # Prepare the list of clusters.
    clusters = []
    for (dendrogram, funs_cluster) in zip(dendrograms, funs_clusters):
        clusters.extend([set([thread_names[funs_cluster[dup]] for dup in dups]) for dups in dendrogram.cut(cut_level, 1)])

    for thread in unique_funs_threads:
        clusters.append(set([thread_names[thread]]))

    # Create new or modify old problems.
    for i, cluster in enumerate(clusters):
        # Find currently stored problems which contain reports from the new cluster.
        problem_ids = set()
        for report_id in cluster:
            problem_id = current_report_problems[report_id]
            if problem_id == None:
                continue
            problem_ids.add(problem_id)

        # If the reports from the new cluster form a majority in a currently stored
        # problem, reuse it instead of creating a new problem.
        reuse_problem = False
        if len(problem_ids) >= 1:
            problem_id = max(problem_ids, key=lambda problem_id: \
                    len(current_problems[problem_id] & cluster))
            if len(current_problems[problem_id] & cluster) > \
                    len(current_problems[problem_id]) / 2:
                reuse_problem = True

        if reuse_problem:
            # If the reports from the problem are equal to the cluster, there is nothing to do.
            if current_problems[problem_id] == cluster:
                logging.debug("[ {0} / {1} ] Skipping existing problem #{2} with reports: {3}.".\
                        format(i + 1, len(clusters), problem_id, sorted(list(cluster))))
                continue

            # Otherwise fetch the problem which will be modified.
            problem = db.session.query(Problem).filter(Problem.id == problem_id).one()

            logging.debug("[ {0} / {1} ] Reusing existing problem #{2} with reports: {3} for reports: {4}.".\
                    format(i + 1, len(clusters), problem_id, sorted(list(current_problems[problem_id])),
                        sorted(list(cluster))))
        else:
            # Create a new problem.
            problem = Problem()
            db.session.add(problem)

            logging.debug("[ {0} / {1} ] Creating new problem for reports: {2}.".\
                    format(i + 1, len(clusters), sorted(list(cluster))))

        # For now, only one OpSys per cluster is supported.
        report_opsys_ids = set([opsys_ids[report_id] for report_id in cluster])
        if(len(report_opsys_ids) > 1):
            logging.warning('Only one OpSys per cluster is supported, skipping')
            continue

        opsys_id = list(report_opsys_ids)[0]

        report_components = set([component_names[report_id] for report_id in cluster])

        if len(report_components) > 1:
            # Prepare a list of common components in report backtraces.

            components_lists = pyfaf.ureport.get_frame_components(cluster, opsys_id, db)

            # Add the report components to the lists.
            for component_list, report_id in zip(components_lists, cluster):
                component_list.append(component_names[report_id])

            components_lists = pyfaf.cluster.filter_components_lists(components_lists)
            common_components = pyfaf.cluster.get_common_components(components_lists)
            ordered_components = pyfaf.cluster.get_ordered_components(common_components, components_lists)
        else:
            # With only one report component just use that component.
            ordered_components = list(report_components)

        # Drop unknown components.
        components = [component for component in ordered_components if component != None]

        logging.debug("Setting problem components to: {0}.".format(components))

        if len(components) > 0:
            # Fetch the components from db and sort them as in ordered_components.
            components = db.session.query(OpSysComponent).\
                    filter((OpSysComponent.name.in_(components)) & \
                        (OpSys.id == opsys_id)).all()
            components.sort(key=lambda c: ordered_components.index(c.name))

        # Set problem for all reports in the cluster and update it.
        for report in db.session.query(Report).filter(Report.id.in_(cluster)).all():
            report.problem = problem

            if not problem.first_occurence or problem.first_occurence > report.first_occurence:
                problem.first_occurence = report.first_occurence
            if not problem.last_occurence or problem.last_occurence < report.last_occurence:
                problem.last_occurence = report.last_occurence

        # Update the problem component list.
        db.session.query(ProblemComponent).filter(ProblemComponent.problem == problem).delete()
        for j, component in enumerate(components):
            problemcomponent = ProblemComponent()
            problemcomponent.problem = problem
            problemcomponent.component = component
            problemcomponent.order = j
            db.session.add(problemcomponent)

        if len(db.session.new) + len(db.session.dirty) > 100:
            db.session.flush()

    db.session.flush()

    # Remove problems which are not referenced by any report.
    logging.info("Removing unreferenced problems.")
    used_problem_ids = db.session.query(Report.problem_id)
    old_problem_ids = db.session.query(Problem.id).\
            filter(func.not_(Problem.id.in_(used_problem_ids)))
    old_problem_components = db.session.query(ProblemComponent).\
            filter(ProblemComponent.problem_id.in_(old_problem_ids))
    old_problem_components.delete(synchronize_session=False)
    old_problem_ids.delete(synchronize_session=False)
