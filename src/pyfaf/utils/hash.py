# Copyright (C) 2015  ABRT Team
# Copyright (C) 2015  Red Hat, Inc.
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

import hashlib

__all__ = ["hash_list", "hash_path"]


def hash_list(inlist):
    '''
    Return hash digest from `inlist` list of strings.

    Strings are concatenated with newlines prior to hashing
    '''

    merged = "\n".join(inlist)
    return hashlib.sha1(merged.encode("utf-8")).hexdigest()


def hash_path(path, prefixes):
    """
    Returns path with part after prefixes hashed with sha256

    In case of paths starting with /home, ignore username.

    Example:
        hash_path("/home/user/a.out", ["/home", "/opt"]) =
        "/home/1816a735235f2a21efd602ff4d9b157bf060540270230597923af0aa6de780e9"

        hash_path("/usr/local/private/code.src", ["/usr/local"]) =
        "/usr/local/039580e05aa4fcec4fbb57e0532311c399453950b741041bce8e72d17698416f"
    """

    for prefix in prefixes:
        if path.startswith(prefix):
            _, rest = path.split(prefix, 1)
            rest = rest[1:]  # remove leading /

            if prefix == "/home":
                _, rest = rest.split('/', 1)

            hashed = hashlib.sha256(rest.encode("utf-8")).hexdigest()

            return "{0}/{1}".format(prefix, hashed)
    return path
