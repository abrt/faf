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
import subprocess
import re

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

def backtrace_similarity(optimized_backtrace_path1, optimized_backtrace_path2):
    # Call doubleparser to get the distances of the bugs
    doubleparser_args = ['doubleparser', '--optimized',
                         optimized_backtrace_path1,
                         optimized_backtrace_path2]
    doubleparser_proc = subprocess.Popen(doubleparser_args, stdout=subprocess.PIPE)
    stdout = doubleparser_proc.communicate()[0]
    if doubleparser_proc.returncode != 0:
        return None

    # Get Levenshtein distance for our two backtraces.
    match = re.search("Levenshtein distance of these two backtraces is (-?[0-9]+)", stdout)
    if match is None:
        print("Failed to match Levenshtein distance.")
    levenshtein_distance = int(match.group(1))

    # Check for Jaccard distance.
    match = re.search("Jaccard distance of these two backtraces is (-?(\d+(\.\d*)))", stdout)
    if match is None:
        print("Failed to match Jaccard distance.")
    jaccard_distance = float(match.group(1))

    # Check for Jaro-Winkler distance.
    match = re.search("Jaro-Winkler distance of these two backtraces is (-?(\d+(\.\d*)))", stdout)
    if match is None:
        print("Failed to match Jaro-Winkler distance.")
    jaro_winkler_distance = float(match.group(1))

    return (levenshtein_distance, jaccard_distance, jaro_winkler_distance)
