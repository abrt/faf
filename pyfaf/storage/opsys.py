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

from . import Architecture
from . import Boolean
from . import Column
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import ProjRelease
from . import String
from . import relationship

class OpSys(GenericTable):
    __tablename__ = "opsys"

    __columns__ = [ Column("id", String(16), primary_key=True),
                    Column("name", String(32), nullable=False) ]

class BuildSystem(GenericTable):
    __tablename__ = "buildsys"

    __columns__ = [ Column("opsys_id", String(16), ForeignKey("{0}.id".format(OpSys.__tablename__)), primary_key=True),
                    Column("xmlrpc_url", String(256), nullable=True),
                    Column("package_url", String(256), nullable=True) ]

    __relationships__ = { "opsys": relationship(OpSys) }

class OpSysRelease(GenericTable):
    __tablename__ = "opsysreleases"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("opsys_id", String(16), ForeignKey("{0}.id".format(OpSys.__tablename__)), nullable=False, index=True),
                    Column("version", String(32), nullable=False) ]

    __relationships__ = { "opsys": relationship(OpSys) }

class Tag(GenericTable):
    __tablename__ = "tags"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("opsys_id", String(16), ForeignKey("{0}.id".format(OpSys.__tablename__)), index=True),
                    Column("name", String(32), nullable=False, unique=True, index=True),
                    Column("perm", Integer, nullable=True),
                    Column("locked", Boolean, nullable=False) ]

    __relationships__ = { "opsys": relationship(OpSys) }

class ArchTag(GenericTable):
    __tablename__ = "archtags"

    __columns__ = [ Column("tag_id", Integer, ForeignKey("{0}.id".format(Tag.__tablename__)), primary_key=True),
                    Column("arch", String(8), ForeignKey("{0}.arch".format(Architecture.__tablename__)), primary_key=True) ]

    __relationships__ = { "tag": relationship(Tag) }

class TagInheritance(GenericTable):
    __tablename__ = "inheritances"

    __columns__ = [ Column("tag_id", Integer, ForeignKey("{0}.id".format(Tag.__tablename__)), primary_key=True),
                    Column("parent_id", Integer, ForeignKey("{0}.id".format(Tag.__tablename__)), primary_key=True),
                    Column("intransitive", Boolean, nullable=False),
                    Column("priority", Integer, nullable=False),
                    Column("noconfig", Boolean, nullable=False) ]

    __relationships__ = { "tag": "relationship(Tag, primaryjoin=cls.table.c.tag_id == Tag.id)",
                          "parent": "relationship(Tag, primaryjoin=cls.table.c.parent_id == Tag.id)" }

class OpSysReleaseComponent(GenericTable):
    __tablename__ = "opsysreleases_components"
    __columns__ = [ Column("opsysreleases_id", Integer, ForeignKey("opsysreleases.id"), primary_key=True),
                    Column("components_id", Integer, ForeignKey("components.id"), primary_key=True) ]

class Component(GenericTable):
    __tablename__ = "components"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("name", String(32), nullable=False, index=True) ]

    __relationships__ = { "opsysreleases": "relationship(OpSysRelease, secondary=OpSysReleaseComponent.table)" }

class Build(GenericTable):
    __tablename__ = "builds"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("projrelease_id", Integer, ForeignKey("{0}.id".format(ProjRelease.__tablename__)), nullable=True, index=True),
                    Column("component_id", Integer, ForeignKey("{0}.id".format(Component.__tablename__)), nullable=False, index=True),
                    Column("tag_id", Integer, ForeignKey("{0}.id".format(Tag.__tablename__)), nullable=True, index=True),
                    Column("revision", String(32), nullable=False) ]

    __relationships__ = { "projrelease": relationship(ProjRelease),
                          "component": relationship(Component),
                          "tag": relationship(Tag) }

class Package(GenericTable):
    __tablename__ = "packages"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("build_id", Integer, ForeignKey("{0}.id".format(Build.__tablename__)), nullable=False, index=True),
                    Column("arch", String(8), ForeignKey("{0}.arch".format(Architecture.__tablename__)), nullable=False, index=True),
                    Column("name", String(64), nullable=False, index=True) ]

    __relationships__ = { "build": relationship(Build) }

    __lobs__ = { "package": 1 << 31 }

class Provides(GenericTable):
    __tablename__ = "provides"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("package_id", Integer, ForeignKey("{0}.id".format(Package.__tablename__)), nullable=False, index=True),
                    Column("provides", String(256), nullable=False, index=True),
                    Column("flags", Integer, nullable=False),
                    Column("version", String(8), nullable=True) ]

    __relationships__ = { "package": relationship(Package) }

class Requires(GenericTable):
    __tablename__ = "requires"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("package_id", Integer, ForeignKey("{0}.id".format(Package.__tablename__)), nullable=False, index=True),
                    Column("requires", String(256), nullable=False, index=True),
                    Column("flags", Integer, nullable=False),
                    Column("version", String(8), nullable=True) ]

    __relationships__ = { "package": relationship(Package) }

class Conflicts(GenericTable):
    __tablename__ = "conflicts"

    __columns__ = [ Column("id", Integer, primary_key=True),
                    Column("package_id", Integer, ForeignKey("{0}.id".format(Package.__tablename__)), nullable=False, index=True),
                    Column("conflicts", String(256), nullable=False, index=True),
                    Column("flags", Integer, nullable=False),
                    Column("version", String(8), nullable=True) ]

    __relationships__ = { "package": relationship(Package) }
