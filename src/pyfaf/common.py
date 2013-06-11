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

import errno
import logging
import os
import re
from pyfaf.config import config

__all__ = ["FafError",
           "Plugin",
           "import_dir",
           "load_plugins",
           "load_plugin_types",
           "log",
           ]

RE_PLUGIN_NAME = re.compile(r"^[a-zA-Z0-9\-]+$")

# Initialize common logging
logging.basicConfig()

# Invalid name "log" for type constant
# pylint: disable-msg=C0103
log = logging.getLogger(name="faf")
# pylint: enable-msg=C0103

def import_dir(module, dirname):
    """
    Imports python files from `dirname` into `module`.
    Ignores files whose name starts with underscore.
    """

    for filename in os.listdir(dirname):
        if not filename.endswith(".py"):
            continue
        if filename.startswith("_"):
            continue

        plugin = "{0}.{1}".format(module, filename[:-3])

        try:
            __import__(plugin, {}, {}, [module])
        except Exception as ex:
            log.error("Unable to import plugin {0}: {1}"
                      .format(plugin, str(ex)))
            raise

def load_plugins(cls, result=None, regexp=RE_PLUGIN_NAME):
    """
    Loads plugins (subclasses of `cls`) into `result` dictionary.
    Each plugin must contain a `name` attribute unique among other plugins
    of the same type (sharing the superclass). Plugin name must match `regexp`.
    """

    if result is None:
        result = {}

    for plugin in cls.__subclasses__():
        classname = plugin.__name__

        if not hasattr(plugin, "name"):
            log.error("Class {0} does not provide 'name' attribute. Each "
                      "subclass of {1} class must provide a unique 'name' "
                      "attribute.".format(classname, cls.__name__))
        elif not regexp.match(plugin.name):
            log.error("Invalid system name '{0}' in class {1}. {2} name "
                      "must match the following regular expression: '{3}'."
                      .format(plugin.name, classname,
                              cls.__name__, regexp.pattern))
        elif plugin.name in result:
            log.error("A {0} plugin named '{1}' is already registered. It is "
                      "implemented in {2} class. Please choose a different "
                      "name.".format(cls.__name__, plugin.name, classname))
        else:
            log.debug("Registering {0} plugin '{1}': {2}"
                      .format(cls.__name__, plugin.name, classname))
            result[plugin.name] = plugin()
            continue

        log.error("{0} plugin {1} will be disabled."
                  .format(cls.__name__, classname))

    return result


def load_plugin_types(cls, result=None):
    """
    Load plugin types (subclasses of `cls`) into `result` dictionary.
    """

    if result is None:
        result = {}

    for plugin in cls.__subclasses__():
        result[plugin.__name__.lower()] = plugin

    return result


def ensure_dirs(dirnames):
    for dirname in dirnames:
        try:
            os.makedirs(dirname)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise FafError("Required directory '{0}' does not "
                               "exist and can't be created: {1}"
                               .format(dirname, ex.strerror))

def get_libname(path):
    libname = os.path.basename(path)
    idx = libname.rfind(".so")
    if idx > 0:
        libname = libname[0:idx + 3]
    return libname

# ToDo:
# just copy-pasted to satisfy storage import

RE_SIGNAL = re.compile('SIG[^)]+')

def format_reason(rtype, reason, function_name):
    if rtype == 'USERSPACE':
        res = RE_SIGNAL.search(reason)
        if res:
            return '{0} in {1}'.format(res.group(), function_name)

        return 'Crash in {0}'.format(function_name)

    if rtype == 'PYTHON':
        spl = reason.split(':')
        if spl >= 4:
            fname, line, loc, exception = spl[:4]
            if loc == '<module>':
                loc = '{0}:{1}'.format(fname, line)
            return '{0} in {1}'.format(exception, loc)

        return 'Exception'

    if rtype == 'KERNELOOPS':
        return 'Kerneloops'

    return 'Crash'

# end ToDo

class FafError(Exception):
    """
    An exception for project-specific errors.
    """

    pass

class Plugin(object):
    """
    A common superclass for all plugins.
    """

    # Unused argument
    # pylint: disable-msg=W0613
    def __init__(self, *args, **kwargs):
        if self.__class__.__name__ == "Plugin":
            # Class 'Plugin' has no '__subclasses__' member
            # pylint: disable-msg=E1101
            subcls = ", ".join([c.__name__ for c in Plugin.__subclasses__()])

            raise FafError("You need to subclass the one of the {0} classes "
                           "in order to implement a plugin.".format(subcls))

        # initialize logging by classname
        self._logger = log.getChild(self.__class__.__name__)
        self.log_debug = self._logger.debug
        self.log_info = self._logger.info
        self.log_warn = self._logger.warn
        self.log_error = self._logger.error
        self.log_critical = self._logger.critical
    # pylint: enable-msg=W0613

    def load_config_to_self(self, selfkey, configkeys, default, callback=None):
        """
        Iterates through `configkeys` and searches each key in the
        configuration. On first match, the config value is saved into
        `self.$selfkey`. If no key is found, `default` is used. By default
        the value is string. If callback is not None, it is called on
        the string and the result is saved into `self.$selfkey`. This is
        useful for type conversions (e.g. callback=int).
        """

        value = default
        for key in configkeys:
            if key not in config:
                continue

            if callback is not None:
                value = callback(config[key])
            else:
                value = config[key]

            break

        self.__setattr__(selfkey, value)
