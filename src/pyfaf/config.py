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

import os
import logging

import sys
if sys.version_info.major == 2:
#Python 2
    import ConfigParser as configparser
else:
#Python 3+
    import configparser

from pyfaf.local import etc, var

__all__ = ["config"]

MAIN_CONFIG_DIR = os.path.join(etc, "faf")
MAIN_CONFIG_FILE = "faf.conf"
CONFIG_FILE_SUFFIX = ".conf"
CONFIG_FILE_ENV_VAR = "FAF_CONFIG_FILE"
CONFIG_CHILD_SECTIONS = ["main.pluginsdir"]


def get_config_files(directory):
    """
    Scan `directory` for files whose name end with `CONFIG_FILE_SUFFIX`
    and return their full paths.
    """

    return [fname for fname in [os.path.abspath(os.path.join(directory, filename))
                                for filename in os.listdir(directory)] if fname.endswith(CONFIG_FILE_SUFFIX)]


def load_config_files(config_files):
    """
    Read given config files and return a dictionary with all specified options.
    """

    result = {}
    parser = configparser.SafeConfigParser()
    parser.read(config_files)

    for section in parser.sections():
        for option in parser.options(section):
            key = "{0}.{1}".format(section.lower(), option.lower())
            result[key] = parser.get(section, option)

    return result


def load_config():
    """
    Read the configuration from all supported places.
    """

    result = {}
    main_config_files = [os.path.join(MAIN_CONFIG_DIR, MAIN_CONFIG_FILE)]

    if CONFIG_FILE_ENV_VAR in os.environ:
        fpath = os.environ[CONFIG_FILE_ENV_VAR]
        if os.access(fpath, os.R_OK):
            main_config_files = [fpath]
        else:
            logging.error("Config file specified by {0} environment variable"
                          " ({1}) not found or unreadable".format(
                              CONFIG_FILE_ENV_VAR, fpath))

    cfg = load_config_files(main_config_files)

    plugin_config_files = []
    for section in CONFIG_CHILD_SECTIONS:
        if section in cfg:
            plugins_dir = os.path.join(MAIN_CONFIG_DIR, cfg[section])
            plugin_config_files = get_config_files(plugins_dir)

    # append main_config_files to the end so that plugins can't override it
    result = load_config_files(plugin_config_files + main_config_files)

    return result


def load_paths(config):
    """
    Populate pyfaf.config.paths with commonly used paths
    """

    if "ureport.directory" in config:
        spool_dir = config["ureport.directory"]
    elif "report.spooldirectory" in config:
        spool_dir = config["report.spooldirectory"]
    else:
        spool_dir = os.path.join(var, "spool", "faf")

    if "dumpdir.cachedirectory" in config:
        dump_dir = config["dumpdir.cachedirectory"]
    else:
        dump_dir = os.path.join(spool_dir, "dumpdirs")

    return {
        "spool": spool_dir,
        "reports": os.path.join(spool_dir, "reports"),
        "reports_deferred": os.path.join(spool_dir, "reports", "deferred"),
        "reports_incoming": os.path.join(spool_dir, "reports", "incoming"),
        "reports_saved": os.path.join(spool_dir, "reports", "saved"),
        "attachments": os.path.join(spool_dir, "attachments"),
        "attachments_deferred": os.path.join(spool_dir, "attachments",
                                             "deferred"),
        "attachments_incoming": os.path.join(spool_dir, "attachments",
                                             "incoming"),
        "attachments_saved": os.path.join(spool_dir, "attachments", "saved"),
        "dumpdir": dump_dir,
    }

# read config on import

# Invalid name "config" for type constant
# pylint: disable-msg=C0103
config = load_config()

# populate paths
paths = load_paths(config)
