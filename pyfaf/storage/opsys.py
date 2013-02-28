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
from . import Boolean
from . import Column
from . import DateTime
from . import Enum
from . import ForeignKey
from . import GenericTable
from . import Integer
from . import ProjRelease
from . import String
from . import UniqueConstraint
from . import relationship

OpSysReleaseStatus = Enum("INVALID_STATUS_CODE", "ACTIVE", "ADDED", "APPROVED",
                          "AWAITING_BRANCH", "AWAITING_DEVELOPMENT", "AWAITING_QA",
                          "AWAITING_PUBLISH", "AWAITING_REVIEW", "EOL", "DENIED",
                          "MAINTENANCE", "MODIFIED", "OBSOLETE", "ORPHANED",
                          "OWNED", "REJECTED", "REMOVED", "UNDER_DEVELOPMENT",
                          "UNDER_REVIEW", "DEPRECATED", name="opsysrelease_status")

class Arch(GenericTable):
    __tablename__ = "archs"
    __table_args__ = ( UniqueConstraint('name'), )

    id = Column(Integer, primary_key=True)
    name = Column(String(8), nullable=False)

    def __str__(self):
        return self.name

class OpSys(GenericTable):
    __tablename__ = "opsys"
    __table_args__ = ( UniqueConstraint('name'), )

    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)

    def __str__(self):
        return self.name

class BuildSystem(GenericTable):
    __tablename__ = "buildsys"

    opsys_id = Column(Integer, ForeignKey("{0}.id".format(OpSys.__tablename__)), primary_key=True)
    xmlrpc_url = Column(String(256), nullable=True)
    package_url = Column(String(256), nullable=True)
    opsys = relationship(OpSys)

class OpSysRelease(GenericTable):
    __tablename__ = "opsysreleases"
    __table_args__ = ( UniqueConstraint('opsys_id', 'version'), )

    id = Column(Integer, primary_key=True)
    opsys_id = Column(Integer, ForeignKey("{0}.id".format(OpSys.__tablename__)), nullable=False, index=True)
    version = Column(String(32), nullable=False)
    releasedate = Column(DateTime, nullable=True)
    status = Column(OpSysReleaseStatus, nullable=False)
    opsys = relationship(OpSys, backref="releases")

    def __str__(self):
        return '{0} {1}'.format(self.opsys, self.version)

class ArchTag(GenericTable):
    __tablename__ = "archstags"

    tag_id = Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True)
    arch_id = Column("arch_id", Integer, ForeignKey("{0}.id".format(Arch.__tablename__)), primary_key=True)
    tag = relationship("Tag")
    arch = relationship(Arch)

class Tag(GenericTable):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    secondary_id = Column(Integer, nullable=False)
    opsys_id = Column(Integer, ForeignKey("{0}.id".format(OpSys.__tablename__)), index=True)
    name = Column(String(32), nullable=False, index=True)
    perm = Column(Integer, nullable=True)
    locked = Column(Boolean, nullable=False)
    opsys = relationship(OpSys, backref="tags")
    #pylint:disable=E1101
    # Class has no '__table__' member
    archs = relationship(Arch, secondary=ArchTag.__table__)

class TagInheritance(GenericTable):
    __tablename__ = "taginheritances"

    tag_id = Column(Integer, ForeignKey("{0}.id".format(Tag.__tablename__)), primary_key=True)
    parent_id = Column(Integer, ForeignKey("{0}.id".format(Tag.__tablename__)), primary_key=True)
    intransitive = Column(Boolean, nullable=False)
    priority = Column(Integer, nullable=False)
    noconfig = Column(Boolean, nullable=False)
    tag = relationship(Tag, primaryjoin="TagInheritance.tag_id == Tag.id")
    parent = relationship(Tag, primaryjoin="TagInheritance.parent_id == Tag.id")

class AssociatePeople(GenericTable):
    __tablename__ = "associatepeople"
    __table_args__ = ( UniqueConstraint('name'), )

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, index=True)

class OpSysReleaseComponentAssociate(GenericTable):
    __tablename__ = "opsysreleasescomponentsassociates"

    opsysreleasecompoents_id = Column(Integer, ForeignKey("opsysreleasescomponents.id"), primary_key=True)
    associatepeople_id = Column(Integer, ForeignKey("associatepeople.id"), primary_key=True)

class OpSysReleaseComponent(GenericTable):
    __tablename__ = "opsysreleasescomponents"
    __table_args__ = ( UniqueConstraint('opsysreleases_id', 'components_id'), )

    id = Column(Integer, primary_key=True)
    opsysreleases_id = Column(Integer, ForeignKey("opsysreleases.id"), nullable=False, index=True)
    components_id = Column(Integer, ForeignKey("opsyscomponents.id"), nullable=False, index=True)
    release = relationship(OpSysRelease, backref="parent_assocs")
    people = relationship(AssociatePeople, secondary=OpSysReleaseComponentAssociate.__table__)

class OpSysComponent(GenericTable):
    __tablename__ = "opsyscomponents"
    __table_args__ = ( UniqueConstraint('opsys_id', 'name'), )

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, index=True)
    opsys_id = Column(Integer, ForeignKey("{0}.id".format(OpSys.__tablename__)), nullable=False, index=True)
    opsys = relationship(OpSys, backref="components")
    #pylint:disable=E1101
    # Class has no '__table__' member
    opsysreleases = relationship(OpSysReleaseComponent, backref="parent")

class BuildTag(GenericTable):
    __tablename__ = "buildstags"

    build_id = Column(Integer, ForeignKey("builds.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("{0}.id".format(Tag.__tablename__)), primary_key=True)

class Build(GenericTable):
    __tablename__ = "builds"

    id = Column(Integer, primary_key=True)
    secondary_id = Column(Integer, nullable=True)
    projrelease_id = Column(Integer, ForeignKey("{0}.id".format(ProjRelease.__tablename__)), nullable=True, index=True)
    component_id = Column(Integer, ForeignKey("{0}.id".format(OpSysComponent.__tablename__)), nullable=False, index=True)
    epoch = Column(Integer, nullable=False)
    version = Column(String(64), nullable=False)
    release = Column(String(64), nullable=False)
    projrelease = relationship(ProjRelease)
    component = relationship(OpSysComponent, backref="builds")
    #pylint:disable=E1101
    # Class has no '__table__' member
    tags = relationship(Tag, secondary=BuildTag.__table__)

    def nvr(self):
        return "{0}-{1}-{2}".format(self.component.name, self.version, self.release)

    def nevr(self):
        if not self.epoch:
            return self.nvr()
        return "{0}-{1}:{2}-{3}".format(self.component.name, self.epoch, self.version, self.release)

class BuildArch(GenericTable):
    __tablename__ = "buildarchs"
    __lobs__ = { "build.log": 1 << 26, "state.log": 1 << 16, "root.log": 1 << 26 }

    build_id = Column(Integer, ForeignKey("{0}.id".format(Build.__tablename__)), primary_key=True)
    arch_id = Column(Integer, ForeignKey("{0}.id".format(Arch.__tablename__)), primary_key=True)

    build = relationship(Build)
    arch = relationship(Arch)

class Package(GenericTable):
    __tablename__ = "packages"
    __lobs__ = { "package": 1 << 31 }

    id = Column(Integer, primary_key=True)
    secondary_id = Column(Integer, nullable=True)
    build_id = Column(Integer, ForeignKey("{0}.id".format(Build.__tablename__)), nullable=False, index=True)
    arch_id = Column(Integer, ForeignKey("{0}.id".format(Arch.__tablename__)), nullable=False, index=True)
    name = Column(String(64), nullable=False, index=True)
    pkgtype = Column(Enum("rpm", "deb", "tgz", name="package_type"), nullable=True)
    build = relationship(Build, backref="packages")
    arch = relationship(Arch)

    #pylint:disable=E1103
    # Instance of 'RelationshipProperty' has no 'version' member
    def nvr(self):
        return "{0}-{1}-{2}".format(self.name, self.build.version, self.build.release)

    def nvra(self):
        return "{0}.{1}".format(self.nvr(), self.arch.name)

    def nevr(self):
        if not self.build.epoch:
            return self.nvr()
        return "{0}-{1}:{2}-{3}".format(self.name, self.build.epoch, self.build.version, self.build.release)

    def nevra(self):
        return "{0}.{1}".format(self.nevr(), self.arch.name)

    def filename(self):
        return "{0}.rpm".format(self.nvra())

class PackageDependency(GenericTable):
    __tablename__ = "packagedependencies"

    id = Column(Integer, primary_key=True)
    package_id = Column(Integer, ForeignKey("{0}.id".format(Package.__tablename__)), nullable=False, index=True)
    type = Column(Enum("PROVIDES", "REQUIRES", "CONFLICTS", name="packagedependency_type"), nullable=False, index=True)
    name = Column(String(1024), nullable=False, index=True)
    flags = Column(Integer, nullable=False)
    epoch = Column(Integer, nullable=True)
    version = Column(String(64), nullable=True)
    release = Column(String(64), nullable=True)
    package = relationship(Package, backref="dependencies")
