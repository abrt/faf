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
import pwd
import re
import tempfile
from pyfaf.config import config

__all__ = ["FafError",
           "Plugin",
           "get_temp_dir",
           "import_dir",
           "load_plugins",
           "load_plugin_types",
           "log",
           "get_connect_string",
          ]

RE_PLUGIN_NAME = re.compile(r"^[a-zA-Z0-9\-]+$")

# Initialize common logging


class FafLogger(logging.Logger, object):
    """
    Custom logger class with explicitely defined getChildLogger method.
    We need this because Python 2.6 does not support getChild.
    """

    def __init__(self, name, level="NOTSET"):
        super(FafLogger, self).__init__(name, level=level)

        self._children = set()

    def getChildLogger(self, suffix):
        """
        Get a logger which is a descendant to this one.

        This is a convenience method, such that

        logging.getLogger('abc').getChild('def.ghi')

        is the same as

        logging.getLogger('abc.def.ghi')

        It's useful, for example, when the parent logger is named using
        __name__ rather than a literal string.
        """

        if self.root is not self:
            suffix = '.'.join((self.name, suffix))

        result = self.manager.getLogger(suffix)
        self._children.add(result)

        return result

    def setLevel(self, level):
        """
        Sets the level of the current logger and all of its children loggers.
        """

        self.level = level
        for child in self._children:
            child.setLevel(level)

logging.setLoggerClass(FafLogger)
logging.basicConfig()

# Invalid name "log" for type constant
# pylint: disable-msg=C0103
log = logging.getLogger(name="faf")
# pylint: enable-msg=C0103


def import_dir(module, dirname, prefix=None):
    """
    Imports python files from `dirname` into `module`.
    Ignores files whose name starts with underscore.
    """

    for filename in os.listdir(dirname):
        if not filename.endswith(".py"):
            continue
        if filename.startswith("_"):
            continue
        if prefix and not filename.startswith(prefix):
            continue

        plugin = "{0}.{1}".format(module, filename[:-3])

        try:
            __import__(plugin, {}, {}, [module])
        except Exception as ex:
            log.error("Unable to import plugin {0}: {1}"
                      .format(plugin, str(ex)))
            continue


def load_plugins(cls, result=None, regexp=RE_PLUGIN_NAME, init=True):
    """
    Loads plugins (subclasses of `cls`) into `result` dictionary.
    Each plugin must contain a `name` attribute unique among other plugins
    of the same type (sharing the superclass). Plugin name must match `regexp`.

    If `init` is False, returns types instead of instantiated objects.
    """

    if result is None:
        result = {}

    for plugin in cls.__subclasses__():
        classname = plugin.__name__

        if not hasattr(plugin, "name"):
            log.error("Class {0} does not provide 'name' attribute. Each "
                      "subclass of {1} class must provide a unique 'name' "
                      "attribute.".format(classname, cls.__name__))

        elif plugin.name.startswith("abstract_"):
            # plugin should not be loaded directly, load its subclasses instead
            load_plugins(plugin, result=result, regexp=regexp, init=init)
            continue

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

            if init:
                result[plugin.name] = plugin()
            else:
                result[plugin.name] = plugin
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


def get_temp_dir(subdir=None):
    """
    Get the temp directory path. If storage.tmpdir exists, it will be
    considered temp root, otherwise system default will be used.
    Temp directory is user-specific - to be able to run tools under different
    users. If `subdir` is specified, the appropriate subdirectory is returned.
    """

    if "storage.tmpdir" in config:
        basetmp = config["storage.tmpdir"]
    else:
        basetmp = tempfile.gettempdir()

    username = pwd.getpwuid(os.getuid()).pw_name
    # no functional reason, just avoid 'faf-faf'
    if username == "faf":
        userdir = "faf"
    else:
        userdir = "faf-{0}".format(username)

    if subdir is None:
        return os.path.join(basetmp, userdir)

    return os.path.join(basetmp, userdir, subdir)


def _get_env_or_config(conf_s, env_s, default):
    found = os.environ.get(env_s, None)
    if not found:
        found = config.get(conf_s, None)
        if not found:
            found = default
    return found


def get_connect_string():
    """Create connection string for database from config file."""
    login = ""
    user = _get_env_or_config("storage.dbuser", "PGUSER", "")
    passwd = _get_env_or_config("storage.dbpasswd", "PGPASSWORD", "")
    # password without user does not make sense
    if user:
        if passwd:
            login = user + ":" + passwd
        else:
            login = user

    host = _get_env_or_config("storage.dbhost", "PGHOST", "")
    port = _get_env_or_config("storage.dbport", "PGPORT", "")
    # port without host does not make sense
    if host:
        if port:
            login = login + "@" + host + ":" + str(port)
        else:
            login = login + "@" + host

    return "postgresql://" + login + "/" + _get_env_or_config("storage.dbname", "PGDATABASE", "")


class FafError(Exception):
    """
    An exception for project-specific errors.
    """

    pass


class FafConfigError(Exception):
    """
    An exception for fatal configuration errors
    """

    pass


class Plugin(object):
    """
    A common superclass for all plugins.
    """

    @classmethod
    def install(cls, db, logger=None):
        """
        Executed when self.installed(db) is False. Does nothing by default.
        """

        pass

    @classmethod
    def installed(cls, db):
        """
        Test whether the plugin is installed in `db` or not.
        By default the plugin is considered _installed_.
        """

        return True

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
        self._logger = log.getChildLogger(self.__class__.__name__)
        self.log_debug = self._logger.debug
        self.log_info = self._logger.info
        self.log_warn = self._logger.warn
        self.log_error = self._logger.error
        self.log_critical = self._logger.critical
    # pylint: enable-msg=W0613

    def load_config_to_self(self, selfkey, configkeys, default=None,
                            callback=None):
        """
        Iterates through `configkeys` and searches each key in the
        configuration. On first match, the config value is saved into
        `self.$selfkey`. If no key is found, `default` is used. By default
        the value is string. If callback is not None, it is called on
        the string and the result is saved into `self.$selfkey`. This is
        useful for type conversions (e.g. callback=int).

        `configkeys` can be either string or list of multiple possible
        strings.
        """

        # so we don't iterate over characters if someone (like me)
        # passes string instead of list
        if not isinstance(configkeys, list):
            configkeys = [configkeys]

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
