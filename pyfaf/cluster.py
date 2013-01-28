import btparser

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
