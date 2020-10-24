import errno
import os
from typing import cast, BinaryIO, Optional, Union

from sqlalchemy.ext.declarative import declarative_base

from pyfaf.common import FafError
from pyfaf.config import config

# Parent of all our tables
class GenericTableBase(object):
    __lobs__ = {}

    __table_args__ = ({"mysql_engine": "InnoDB",
                       "mysql_charset": "utf8"})

    def pkstr(self) -> str:
        parts = []
        for col in self.__table__._columns: #pylint: disable=no-member, protected-access
            if col.primary_key:
                parts.append(str(self.__getattribute__(col.name)))

        if not parts:
            raise FafError("No primary key found for object '{0}'".format(self.__class__.__name__))

        return "-".join(parts)

    def get_lob_path(self, name: str) -> str:
        classname = self.__class__.__name__
        if name not in self.__lobs__:
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

    def has_lob(self, name: str) -> bool:
        return os.path.isfile(self.get_lob_path(name))

    # lob for Large OBject
    # in DB: blob = Binary Large OBject, clob = Character Large OBject
    def get_lob(self, name: str) -> Optional[bytes]:
        lobpath = self.get_lob_path(name)

        if not os.path.isfile(lobpath):
            return None

        with open(lobpath, "rb") as lob:
            result = lob.read()

        return result

    def get_lob_fd(self, name: str) -> Optional[BinaryIO]:
        lobpath = self.get_lob_path(name)

        if not os.path.isfile(lobpath):
            return None

        try:
            result: Optional[BinaryIO] = open(lobpath, "rb")
        except: # pylint: disable=bare-except
            result = None

        return result

    def _write_lob_bytes(self, dest: BinaryIO, data: bytes, maxlen: int = 0,
                         truncate: bool = False):
        if len(data) > maxlen > 0:
            if truncate:
                data = data[:maxlen]
            else:
                raise FafError("Data is too long, '{0}' only allows length of {1}".format(dest.name, maxlen))

        dest.write(data)

    def _write_lob_file(self, dest: BinaryIO, src: BinaryIO, maxlen: int = 0,
                        bufsize: int = 4096):
        read = 0
        buf = src.read(bufsize)
        while buf and (maxlen <= 0 or read <= maxlen):
            read += len(buf)
            if read > maxlen > 0:
                buf = buf[:(read - maxlen)]
            dest.write(buf)
            buf = src.read(bufsize)

    def save_lob(self, name: str, data: Union[bytes, BinaryIO],
                 overwrite: bool = False, truncate: bool = False):
        lobpath = self.get_lob_path(name)

        if not isinstance(data, bytes) and not hasattr(data, "read"):
            raise FafError("Cannot save LOB '{0}'. Data must be either "
                           "a bytestring or a file-like object".format(name))

        if not overwrite and os.path.isfile(lobpath):
            raise FafError("Lob '{0}' already exists".format(name))

        maxlen = self.__lobs__[name]

        with open(lobpath, "wb") as lob:
            if hasattr(data, "read"):
                if not truncate:
                    raise FafError("When saving from file, truncate must be enabled")

                data = cast(BinaryIO, data)
                self._write_lob_file(lob, data, maxlen)
            else:
                data = cast(bytes, data)
                self._write_lob_bytes(lob, data, maxlen, truncate)

    def del_lob(self, name: str):
        lobpath = self.get_lob_path(name)

        if not os.path.isfile(lobpath):
            raise FafError("Lob '{0}' does not exist".format(name))

        os.unlink(lobpath)

GenericTable = declarative_base(cls=GenericTableBase)
