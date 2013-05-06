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

import logging
import os
import re
from config import config

__all__ = [ "FafError", "Plugin", "import_dir", "load_plugins", "log" ]

RE_PLUGIN_NAME = re.compile("^[a-zA-Z0-9\-]+$")

# Initialize common logging
logging.basicConfig()
log = logging.getLogger(name="faf")

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
            log.error("Unable to import plugin {0}: {1}".format(plugin, str(ex)))
            raise

def load_plugins(cls, result={}, regexp=RE_PLUGIN_NAME):
    """
    Loads plugins (subclasses of `cls`) into `result` dictionary.
    Each plugin must contain a `name` attribute unique among other plugins
    of the same type (sharing the superclass). Plugin name must match `regexp`.
    """

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

userspace = re.compile('SIG[^)]+')

# ToDo:
# just copy-pasted to satisfy storage import
def format_reason(rtype, reason, function_name):
    if rtype == 'USERSPACE':
        res = userspace.search(reason)
        if res:
            return '{0} in {1}'.format(res.group(), function_name)

        return 'Crash in {0}'.format(function_name)

    if rtype == 'PYTHON':
        spl = reason.split(':')
        if spl >= 4:
            file, line, loc, exception = spl[:4]
            if loc == '<module>':
                loc = '{0}:{1}'.format(file, line)
            return '{0} in {1}'.format(exception, loc)

        return 'Exception'

    if rtype == 'KERNELOOPS':
        return 'Kerneloops'

    return 'Crash'

class FafError(Exception):
    """
    An exception for project-specific errors.
    """

    pass

class NoRaise(object):
    """
    A decorator that catches exceptions from the function
    """

    def __init__(self, catch=Exception, loglevel=logging.ERROR, debug=False):
        self.catch = catch
        self.loglevel = loglevel
        self.debug = debug

    def __call__(self, func):
        self.func = func
        return self._run

    def _log(self, msg):
        log.log(self.loglevel, msg)

    def _run(self, *args, **kwargs):
        try:
            self.func(*args, **kwargs)
        except self.catch as ex:
            self._log("Function '{0}' has raised an unhandled exception"
                      .format(self.func.__name__))
            self._log("{0}: {1}".format(ex.__class__.__name__, str(ex)))

            if self.debug:
                raise

class Plugin(object):
    """
    A common superclass for all plugins.
    """

    def __init__(self, *args, **kwargs):
        if self.__class__.__name__ == "Plugin":
            subclasses = ", ".join([c.__name__ for c in Plugin.__subclasses__()])

            raise FafError("You need to subclass the one of the {0} classes "
                           "in order to implement a plugin.".format(subclasses))

        # initialize logging by classname
        self._logger = log.getChild(self.__class__.__name__)
        self.log_debug = self._logger.debug
        self.log_info = self._logger.info
        self.log_warn = self._logger.warn
        self.log_error = self._logger.error
        self.log_critical = self._logger.critical

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
