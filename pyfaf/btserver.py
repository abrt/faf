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
import btparser
import run
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
    # Call btparser to get the distance of the bugs
    btparser_args = ['btparser', '--distances', '--comparison-optimized',
                         optimized_backtrace_path1,
                         optimized_backtrace_path2]
    btparser_proc = subprocess.Popen(btparser_args, stdout=subprocess.PIPE)
    stdout = btparser_proc.communicate()[0]
    if btparser_proc.returncode != 0:
        return None
    lines = stdout.splitlines()
    if len(lines) != 2:
        return None
    fields = lines[0].split()
    if len(fields) != 2:
        return None

    return float(fields[1])

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

def get_original_component(db, bug):
    # Return the component which owns the crashed application
    db.execute("SELECT body FROM rhbz_comment WHERE id = {0}".format(bug.comments[0]))
    comment = db.fetchall()[0][0]
    for line in comment.splitlines():
        if line.startswith("executable: "):
            return get_component_by_file(db, line.split()[1])

def get_backtrace(db, bug_id):
    # Return parsed backtrace for the specified bug id
    db.execute("SELECT id FROM rhbz_attachment WHERE file_name = 'backtrace' and bug_id = {0} ORDER BY id DESC".format(bug_id))
    for row in db.fetchall():
        try:
            attachment = str(run.cache_get("rhbz-attachment", row[0]).contents)
            backtrace = btparser.Backtrace(attachment)
            break
        except:
            pass
    return backtrace

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
    backtrace = get_backtrace(db, bug_id)
    thread = get_crash_thread(backtrace)
    components = []
    for frame in thread.frames:
        lib = backtrace.find_address(frame.get_address())
        if isinstance(lib, btparser.Sharedlib):
            component = get_component_by_file(db, lib.get_soname())
            if not uniq or len(components) == 0 or component != components[-1]:
                components.append(component)

    return components
