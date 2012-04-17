# Copyright (C) 2012 Red Hat, Inc.
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

from . import Column
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import String
from . import Package
from . import PackageProvides
from . import UniqueConstraint
from . import relationship
from .. import package
import shutil

class Symbol(GenericTable):
    __tablename__ = "symbols"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("name", String(64), nullable=False),
                    Column("normalized_path", String(512), nullable=False),
                    UniqueConstraint('name', 'normalized_path') ]

class SymbolSource(GenericTable):
    __tablename__ = "symbolsources"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("symbol_id", Integer, ForeignKey("{0}.id".format(Symbol.__tablename__)), nullable=True, index=True),
                    Column("build_id", String(64), nullable=False),
                    Column("path", String(512), nullable=False),
                    Column("offset", Integer, nullable=False),
                    Column("hash", String(64), nullable=True),
                    Column("source_path", String(512), nullable=True),
                    Column("line_number", Integer, nullable=True),
                    UniqueConstraint('build_id', 'path', 'offset') ]

    __relationships__ = { "symbol": relationship(Symbol, backref="sources") }

def retrace_symbols(session):
    #pylint: disable=E1101
    # Class 'SymbolSource' has no 'symbol' member
    symbolSources = session.query(SymbolSource).join(SymbolSource.symbol).filter(Symbol.name == None).group_by(SymbolSource.build_id,SymbolSource.path)

    while any(symbolSources):
        source = symbolSources.pop()

        # Find package providing the build id.
        debuginfo_path = "/usr/lib/debug/.build-id/{0}/{1}.debug".format(source.build_id[:2], source.build_id[2:])

        #pylint: disable=E1103
        # Class 'Package' has no 'provides' member (but some types
        # could not be inferred)
        debuginfo_packages = session.query(Package).join(Package.provides).filter(PackageProvides.provides == debuginfo_path)
        for debuginfo_package in debuginfo_packages:
            binary_package = session.query(Package).filter(Package.build_id == debuginfo_package.build_id,
                                                    Package.arch_id == debuginfo_package.arch_id,
                                                    PackageProvides.provides == source.path).first()

            if binary_package is None:
                continue

            binary_dir = package.unpack_rpm_to_tmp(package._get_lobpath("package"),
                                                   prefix="faf-symbol-retrace")
            debuginfo_dir = package.unpack_rpm_to_tmp(debuginfo_package._get_lobpath("package"),
                                                      prefix="faf-symbol-retrace")

            sources = [source]
            while any(symbolSources) and symbolSources[0].build_id == source.build_id and symbolSources[0].path == source.path:
                sources.append(symbolSources.pop())

            for source in sources:
                # addr2line source
                pass

            shutil.rmtree(binary_dir)
            shutil.rmtree(debuginfo_dir)

def retrace_symbol_source(source):
    """
    Returns True if successful, False otherwise.
    """
    return True
