# Various helpers shared by command line tools.
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
import sys
import types
import datetime
import signal
import time
import os
import cache
import config

class Alarm(Exception):
    pass
def alarm_handler(signum, frame):
    raise Alarm

def process(args, stdout=None, stderr=None, inputt=None,
            timeout=None, timeout_attempts=0, returncode_attempts=0):
    proc = subprocess.Popen(args, stdout=stdout, stderr=stderr)
    if timeout is not None:
        signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(timeout)
    try:
        retstdout, retstderr = proc.communicate(inputt)
        signal.alarm(0)  # reset the alarm
    except Alarm:
        try:
            proc.terminate()
        except OSError:
            pass
        if timeout_attempts > 0:
            time.sleep(60) # wait a minute before another attempt
            return process(args, stdout, stderr, inputt, timeout,
                           timeout_attempts - 1, returncode_attempts)
        else:
            sys.stderr.write("Program exited with timeout: {0}.\n".format(args))
            exit(1)
    if proc.returncode != 0:
        if returncode_attempts > 0:
            time.sleep(60) # wait a minute before another attempt
            return process(args, stdout, stderr, inputt, timeout,
                           timeout_attempts, returncode_attempts - 1)
        else:
            sys.stderr.write("Unexpected return code {0} from {1}.\n".format(proc.returncode, args))
            exit(1)
    return unicode(retstdout, encoding='utf-8') if retstdout is not None else None, unicode(retstderr, encoding='utf-8') if retstderr is not None else None

def config_get(option):
    """
    Returns user's configuration value for an option.
    Option is in "Section.OptionName" format. Example: "Bugzilla.User".

    This function returns either None in the case of failure, or a
    string containing the option value.
    """
    return config.get(option)

def config_get_cache_directory():
    cd = config_get("Cache.Directory")
    if cd:
        return os.path.expanduser(cd)
    return None

def target_from_name(name):
    """
    Returns target for a given name. Creates persistent target list and
    database connection.

    The database connection is created with default parameters. If you want to
    use different database handle, you can set the attribute manually.
    """

    if not hasattr(target_from_name, "db"):
        target_from_name.db = cache.Database()

    if not hasattr(target_from_name, "cache_dir"):
        target_from_name.cache_dir = config_get_cache_directory()

    if not hasattr(target_from_name, "target_list"):
        db = target_from_name.db
        cache_dir = target_from_name.cache_dir
        target_from_name.target_list = cache.TargetList(db, cache_dir)

    return target_from_name.target_list.from_directory_name(name)

def cache_list_id(target):
    target = target_from_name(target)
    return [int(ident) for (ident, mtime) in target.list()]

def cache_list_id_mtime(target):
    target = target_from_name(target)
    entry_ids = []
    times = {}
    for (entry_id, timestamp) in target.list():
        entry_ids.append(int(entry_id))
        times[int(entry_id)] = datetime.datetime.fromtimestamp(float(timestamp))
    return entry_ids, times

def cache_get(target_name, entry_id, parser_module=None,
              failure_allowed=False):
    target = target_from_name(target_name)
    try:
        entry_text = target.get(entry_id)
    except:
        if failure_allowed:
            return None
        sys.stderr.write("Failed to get {0} #{1} from cache.\n".format(target_name, entry_id))
        exit(1)

    if parser_module is None:
        parser_module = cache.__dict__[target_name.replace("-", "_")]
    return parser_module.parser.from_text(entry_text, failure_allowed)

def cache_get_path(target_name, entry_id, failure_allowed=False):
    target = target_from_name(target_name)
    try:
        path = target.get_path(entry_id)
    except:
        if failure_allowed:
            return None
        sys.stderr.write("Failed to get {0} #{1} path from cache.\n".format(target_name, entry_id))
        exit(1)
    return path.strip()

def cache_add(entry, overwrite, target_name=None):
    # Find target's parser from cache, depending on the class of entry
    for cache_item, cache_item_object in cache.__dict__.items():
        if not type(cache_item_object) is types.ModuleType:
            continue
        for potential_class in cache_item_object.__dict__.values():
            if not type(potential_class) is types.ClassType:
                continue
            if not isinstance(entry, potential_class):
                continue
            if "parser" not in cache_item_object.__dict__:
                sys.stderr.write("Failed to find parser for module {0}.\n".format(cache_item))
                exit(1)
            entry_text = cache_item_object.__dict__["parser"].to_text(entry)
            if target_name is None:
                target_name = cache_item.replace("_", "-")

            target = target_from_name(target_name)
            try:
                target.add(entry.id, entry_text, overwrite)
            except Exception as e:
                sys.stderr.write("Failed to store {0} to cache.\n".format(target_name))
                sys.stderr.write("Reason: {0}\n".format(e.message))
                exit(1)
            return
    sys.stderr.write("Failed to find corresponding module for {0}.\n".format(entry))
    exit(1)

def cache_add_text(text, entry_id, target_name, overwrite):
    target = target_from_name(target_name)
    try:
        target.add(entry_id, text, overwrite)
    except Exception as e:
        sys.stderr.write("Failed to store {0} #{1} to cache.\n".format(target_name, entry_id))
        sys.stderr.write("Reason: {0}\n".format(e.message))
        exit(1)

def cache_remove(target_name, entry_id, failure_allowed=False):
    target = target_from_name(target_name)
    try:
        target.remove(entry_id)
    except Exception as e:
        if not failure_allowed:
            sys.stderr.write("Failed to remove {0} #{1} from cache.\n".format(target_name, entry_id))
            sys.stderr.write("Reason: {0}\n".format(e.message))
            exit(1)
