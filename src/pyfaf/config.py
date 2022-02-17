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

import configparser
import os
import logging
import logging.config

from typing import Any, Dict, List

from pyfaf.local import etc, var

__all__ = ["config", "configure_logging"]

MAIN_CONFIG_DIR = os.path.join(etc, "faf")
MAIN_CONFIG_FILE = "faf.conf"
MAIN_LOG_CONFIG_FILE = "faf-logging.conf"
CONFIG_FILE_SUFFIX = ".conf"
CONFIG_FILE_ENV_VAR = "FAF_CONFIG_FILE"
CONFIG_LOG_FILE_ENV_VAR = "FAF_LOG_CONFIG_FILE"
CONFIG_CHILD_SECTIONS = ["main.pluginsdir"]


def get_config_files(directory) -> List[str]:
    """
    Scan `directory` for files whose name end with `CONFIG_FILE_SUFFIX`
    and return their full paths.
    """

    return [fname for fname in [os.path.abspath(os.path.join(directory, filename))
                                for filename in os.listdir(directory)] if fname.endswith(CONFIG_FILE_SUFFIX)]


def load_config_files(config_files) -> Dict[str, Any]:
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


def load_config() -> Dict[str, Any]:
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
            logging.error("Config file specified by %s environment variable"
                          " (%s) not found or unreadable", CONFIG_FILE_ENV_VAR, fpath)

    cfg = load_config_files(main_config_files)

    plugin_config_files = []
    for section in CONFIG_CHILD_SECTIONS:
        if section in cfg:
            plugins_dir = os.path.join(MAIN_CONFIG_DIR, cfg[section])
            plugin_config_files = get_config_files(plugins_dir)

    # append main_config_files to the end so that plugins can't override it
    result = load_config_files(plugin_config_files + main_config_files)

    return result

def configure_logging() -> None:
    """
    Load and configure logging from a config file.
    If the config file isn't available, fallback to basic logging.
    """

    config_path = os.path.join(MAIN_CONFIG_DIR, MAIN_LOG_CONFIG_FILE)

    if CONFIG_LOG_FILE_ENV_VAR in os.environ:
        config_path = os.environ[CONFIG_LOG_FILE_ENV_VAR]

    try:
        with open(config_path) as config_file:
            logging.config.fileConfig(config_file)
    except OSError as ex:
        logfmt = "[%(asctime)s] %(levelname)s:%(name)s: %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        logging.basicConfig(format=logfmt, datefmt=datefmt)
        logging.error("Config file not found or unreadable: %s", str(ex))


def load_paths(conf) -> Dict[str, str]:
    """
    Populate pyfaf.config.paths with commonly used paths
    """

    if "ureport.directory" in conf:
        spool_dir = conf["ureport.directory"]
    elif "report.spooldirectory" in conf:
        spool_dir = conf["report.spooldirectory"]
    else:
        spool_dir = os.path.join(var, "spool", "faf")

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
    }

# read config on import

# Invalid name "config" for type constant
# pylint: disable-msg=C0103
config = load_config()

# populate paths
paths = load_paths(config)
