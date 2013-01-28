# Copyright (C) 2011 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import run
import btparser

def build_rpm_dependencies(db, require, rpm_deps):
    """
    Returns a set of rpm ids.
    """
    if require.startswith(u"/"):
        # It's a file, fetching from file table
        db.execute("""SELECT id FROM fedora_koji_rpm, fedora_koji_rpm_files
                       WHERE koji_rpm_id=id AND value=?""", [require])
    else:
        db.execute("""SELECT id FROM fedora_koji_rpm, fedora_koji_rpm_provides
                       WHERE koji_rpm_id=id AND fedora_koji_rpm_provides.name=?""", [require])

    rows = db.fetchall()
    if len(rows) == 0:
        return

    # Get the newest version of the rpm (the highest id of them).
    rpm_id = int(max(rows, key=lambda x:x[0])[0])
    if rpm_id in rpm_deps:
        return
    rpm_deps.add(rpm_id)

    # Recursively find dependencies on current rpm.
    db.execute("""
      SELECT name FROM fedora_koji_rpm_requires
        WHERE koji_rpm_id=?""", [rpm_id])
    requires = [d[0] for d in db.fetchall()]
    for require in requires:
        if require.startswith(u"/bin") or require.startswith(u"/usr/bin"):
            continue
        # rpmlib depenendencies are of no interest for us.
        if require.startswith(u"rpmlib("):
            continue
        build_rpm_dependencies(db, require, rpm_deps)

def all_referenced_components(db, component):
    # Get id of koji builds of the component from the database
    db.execute("SELECT id FROM fedora_koji_build WHERE name=?",
               [component])
    build_ids = [d[0] for d in db.fetchall()]

    rpm_deps = set()
    for build_id in build_ids:
        # Get rpms related to each koji build we found and get name
        # for each rpm we found for every koji build id
        db.execute("""
          SELECT name FROM fedora_koji_rpm, fedora_koji_build_rpms
            WHERE fedora_koji_build_rpms.koji_build_id=?
              AND fedora_koji_rpm.id=value""", [build_id])
        rpm_names = [d[0] for d in db.fetchall()]
        for rpm_name in rpm_names:
            build_rpm_dependencies(db, rpm_name, rpm_deps)

    # Get component names for every rpm from earlier created table.
    component_deps = set()
    for rpm_dep in rpm_deps:
        db.execute("""
          SELECT koji_build_id FROM fedora_koji_build_rpms
            WHERE value=?""", [rpm_dep])
        build_ids = [d[0] for d in db.fetchall()]

        # Change the gained build id into build (component) name.
        for build_id in build_ids:
            db.execute("SELECT name FROM fedora_koji_build WHERE id=?",
                       [build_id])
            build_names = [d[0] for d in db.fetchall()]
            component_deps |= set(build_names)

    return component_deps

file_component_cache = dict()

def get_component_by_file(db, name):
    # Return component which owns the specified file
    if name in file_component_cache:
        return file_component_cache[name]
    db.execute("SELECT fedora_koji_build.name FROM fedora_koji_build, fedora_koji_rpm, fedora_koji_rpm_files WHERE fedora_koji_build.id = build_id AND koji_rpm_id = fedora_koji_rpm.id AND value = ?", [name])
    for row in db.fetchall():
        component = str(row[0])
        break
    else:
        component = None
    file_component_cache[name] = component
    return component

def get_field_from_bz_comment(field, comment):
    text = None
    field += ":"

    for line in comment.splitlines():
        if line == field:
            text = ""
            continue
        if text == None:
            continue
        if line == "":
            break
        if line.startswith(":"):
            if text:
                text += "\n"
            text += line[1:]
        else:
            text += " "
            text += line

    return text

def get_original_component(db, bug):
    # Return the component which owns the crashed application
    comment = run.cache_get("rhbz-comment", bug.comments[0], failure_allowed=True)
    if not comment:
        return None
    for line in comment.body.splitlines():
        if line.startswith("component: "):
            return line.split()[1]
    for line in comment.body.splitlines():
        if line.startswith("executable: "):
            return get_component_by_file(db, line.split()[1])
    return None

def get_backtrace_candidates(bug_id):
    bug = run.cache_get("rhbz-bug", bug_id)

    # First try attachments in reverse order
    for (i, attachment_id) in enumerate(reversed(bug.attachments)):
        attachment = run.cache_get("rhbz-attachment", attachment_id)
        if not attachment.contents or attachment.file_name != "backtrace":
            continue
        yield str(attachment.contents)

    # Then comments in reverse order
    for (i, comment_id) in enumerate(reversed(bug.comments)):
        comment = run.cache_get("rhbz-comment", comment_id)
        if not comment.body:
            continue
        comment = get_field_from_bz_comment("backtrace", comment.body)
        if comment:
            yield comment

def get_backtrace(bug_id):
    # Return parsed backtrace for the specified bug id
    for text in get_backtrace_candidates(bug_id):
        try:
            backtrace = btparser.Backtrace(text)
            return backtrace
        except:
            pass

    raise Exception("No parsable backtrace found for bug {0}".format(bug_id))

def get_crash_thread(backtrace, normalize=True, setlibs=True):
    # Return crash thread
    crash_thread = backtrace.find_crash_thread()
    if not crash_thread:
        return None
    crash_thread_num = crash_thread.get_number()
    if setlibs:
        backtrace.set_libnames()
    if normalize:
        backtrace.normalize()
    for thread in backtrace.threads:
        if thread.get_number() == crash_thread_num:
            return thread
    else:
        assert False

def get_frame_components(db, bug_id, uniq=True):
    # Return list of components corresponding to the frames in crash thread
    backtrace = get_backtrace(bug_id)
    thread = get_crash_thread(backtrace)
    components = []
    for frame in thread.frames:
        lib = backtrace.find_address(frame.get_address())
        if isinstance(lib, btparser.Sharedlib):
            for path in guess_component_paths(lib.get_soname()):
                component = get_component_by_file(db, path)
                if component:
                    break
            if not uniq or len(components) == 0 or component != components[-1]:
                components.append(component)

    return components

def get_optimized_thread(backtrace, max_frames=8):
    return backtrace.get_optimized_thread(max_frames)

def get_distances_to_threads(thread, threads):
    # Return distances between the thread and every thread from threads
    all_threads = [thread]
    all_threads.extend(threads)
    distances = btparser.Distances("levenshtein", all_threads, 1)
    return [distances.get_distance(0, 1 + i) for i in xrange(len(threads))]

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
