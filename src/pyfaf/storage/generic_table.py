import errno
import os

from sqlalchemy.ext.declarative import declarative_base

from pyfaf.common import FafError
from pyfaf.config import config

# Parent of all our tables
class GenericTableBase(object):
    __lobs__ = {}

    __table_args__ = ({"mysql_engine": "InnoDB",
                       "mysql_charset": "utf8"})

    def pkstr(self):
        parts = []
        for col in self.__table__._columns: #pylint: disable=no-member, protected-access
            if col.primary_key:
                parts.append(str(self.__getattribute__(col.name)))

        if not parts:
            raise FafError("No primary key found for object '{0}'".format(self.__class__.__name__))

        return "-".join(parts)

    def get_lob_path(self, name):
        classname = self.__class__.__name__
        if not name in self.__lobs__:
            raise FafError("'{0}' does not allow a lob named '{1}'".format(classname, name))

        pkstr = self.pkstr()
        pkstr_long = pkstr
        while len(pkstr_long) < 5:
            pkstr_long = "{0}{1}".format("".join(["0" for i in range(5 - len(pkstr_long))]), pkstr_long)

        lobdir = os.path.join(config["storage.lobdir"], classname, name,
                              pkstr_long[0:2], pkstr_long[2:4])
        try:
            os.makedirs(lobdir)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise

        return os.path.join(lobdir, pkstr)

    def has_lob(self, name):
        return os.path.isfile(self.get_lob_path(name))

    # lob for Large OBject
    # in DB: blob = Binary Large OBject, clob = Character Large OBject
    def get_lob(self, name, binary=True):
        lobpath = self.get_lob_path(name)

        if not os.path.isfile(lobpath):
            return None

        mode = "r"
        if binary:
            mode += "b"
        with open(lobpath, mode) as lob:
            result = lob.read()

        return result

    def get_lob_fd(self, name, binary=True):
        lobpath = self.get_lob_path(name)

        if not os.path.isfile(lobpath):
            return None

        mode = "r"
        if binary:
            mode += "b"

        try:
            result = open(lobpath, mode)
        except: # pylint: disable=bare-except
            result = None

        return result

    def _save_lob_string(self, dest, data, maxlen=0, truncate=False):
        if len(data) > maxlen > 0:
            if truncate:
                data = data[:maxlen]
            else:
                raise FafError("Data is too long, '{0}' only allows length of {1}".format(dest.name, maxlen))

        dest.write(data.encode("utf-8"))

    def _save_lob_file(self, dest, src, maxlen=0, bufsize=4096):
        read = 0
        buf = src.read(bufsize)
        while buf and (maxlen <= 0 or read <= maxlen):
            read += len(buf)
            if read > maxlen > 0:
                buf = buf[:(read - maxlen)]
            dest.write(buf)
            buf = src.read(bufsize)

    def save_lob(self, name, data, binary=True, overwrite=False, truncate=False):
        lobpath = self.get_lob_path(name)

        if not overwrite and os.path.isfile(lobpath):
            raise FafError("Lob '{0}' already exists".format(name))

        maxlen = self.__lobs__[name]
        mode = "w"
        if binary:
            mode += "b"

        with open(lobpath, mode) as lob:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            if isinstance(data, str):
                self._save_lob_string(lob, data, maxlen, truncate)
            elif hasattr(data, "read"):
                if not truncate:
                    raise FafError("When saving from file, truncate must be enabled")

                self._save_lob_file(lob, data, maxlen)
            else:
                raise FafError("Data must be either str, unicode or file-like object")

    def del_lob(self, name):
        lobpath = self.get_lob_path(name)

        if not os.path.isfile(lobpath):
            raise FafError("Lob '{0}' does not exist".format(name))

        os.unlink(lobpath)

GenericTable = declarative_base(cls=GenericTableBase)
