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

from typing import Any, Dict, List, Union

from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Column, ForeignKey, UniqueConstraint, Index
from sqlalchemy.types import Boolean, DateTime, Enum, Integer, String

from .custom_types import Semver
from .generic_table import GenericTable
from .project import ProjRelease

OpSysReleaseStatus = Enum("INVALID_STATUS_CODE", "ACTIVE", "ADDED", "APPROVED",
                          "AWAITING_BRANCH", "AWAITING_DEVELOPMENT", "AWAITING_QA",
                          "AWAITING_PUBLISH", "AWAITING_REVIEW", "EOL", "DENIED",
                          "MAINTENANCE", "MODIFIED", "OBSOLETE", "ORPHANED",
                          "OWNED", "REJECTED", "REMOVED", "UNDER_DEVELOPMENT",
                          "UNDER_REVIEW", "DEPRECATED", name="opsysrelease_status")


class Arch(GenericTable):
    __tablename__ = "archs"
    __table_args__ = (UniqueConstraint('name'),)

    id = Column(Integer, primary_key=True)
    name = Column(String(8), nullable=False)

    def __str__(self) -> str:
        return str(self.name)


class OpSys(GenericTable):
    __tablename__ = "opsys"
    __table_args__ = (UniqueConstraint('name'),)

    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)

    def __str__(self) -> str:
        return str(self.name)

    def __lt__(self, other) -> bool:
        return self.name < other.name

    @property
    def active_releases(self) -> List[Dict[str, Any]]:
        # self.releases is a backref from OpSysRelease.
        # pylint: disable=no-member
        return [release for release in self.releases if release.status == 'ACTIVE']


class Url(GenericTable):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True)
    url = Column(String(256), nullable=False)


class OpSysRelease(GenericTable):
    __tablename__ = "opsysreleases"
    __table_args__ = (UniqueConstraint('opsys_id', 'version'),)

    id = Column(Integer, primary_key=True)
    opsys_id = Column(Integer, ForeignKey(f"{OpSys.__tablename__}.id"), nullable=False, index=True)
    version = Column(String(32), nullable=False)
    releasedate = Column(DateTime, nullable=True)
    status = Column(OpSysReleaseStatus, nullable=False)
    opsys = relationship(OpSys, backref="releases")

    def __str__(self) -> str:
        return f"{self.opsys} {self.version}"

    def __lt__(self, other) -> bool:
        if self.opsys == other.opsys:
            return self.version < other.version
        return self.opsys < other.opsys


class Repo(GenericTable):
    __tablename__ = "repo"

    id = Column(Integer, primary_key=True)
    name = Column(String(256))
    type = Column(Enum("dnf", "yum", "koji", "rpmmetadata", name="repo_type"), nullable=False)
    nice_name = Column(String(256), nullable=True)
    nogpgcheck = Column(Boolean, nullable=False)
    opsys_list = relationship(OpSys, secondary="opsysrepo")
    opsysrelease_list = relationship(OpSysRelease, secondary="opsysreleaserepo")
    arch_list = relationship(Arch, secondary="archrepo")
    url_list = relationship(Url, secondary="urlrepo")

    def __str__(self) -> str:
        return str(self.name)


class OpSysRepo(GenericTable):
    __tablename__ = "opsysrepo"

    opsys_id = Column(Integer, ForeignKey(f"{OpSys.__tablename__}.id"), primary_key=True)
    repo_id = Column(Integer, ForeignKey(f"{Repo.__tablename__}.id"), primary_key=True)


class ArchRepo(GenericTable):
    __tablename__ = "archrepo"

    arch_id = Column(Integer, ForeignKey(f"{Arch.__tablename__}.id"), primary_key=True)
    repo_id = Column(Integer, ForeignKey(f"{Repo.__tablename__}.id"), primary_key=True)

class UrlRepo(GenericTable):
    __tablename__ = "urlrepo"

    url_id = Column(Integer, ForeignKey(f"{Url.__tablename__}.id"), primary_key=True)
    repo_id = Column(Integer, ForeignKey(f"{Repo.__tablename__}.id"), primary_key=True)


class OpSysReleaseRepo(GenericTable):
    __tablename__ = "opsysreleaserepo"

    opsysrelease_id = Column(Integer, ForeignKey(f"{OpSysRelease.__tablename__}.id"),
                             primary_key=True)
    repo_id = Column(Integer, ForeignKey(f"{Repo.__tablename__}.id"), primary_key=True)


class OpSysComponent(GenericTable):
    __tablename__ = "opsyscomponents"
    __table_args__ = (UniqueConstraint("opsys_id", "name"),)

    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False, index=True)
    opsys_id = Column(Integer, ForeignKey(f"{OpSys.__tablename__}.id"),
                      nullable=False, index=True)
    opsys = relationship(OpSys, backref="components")

    def __str__(self) -> str:
        return str(self.name)


class OpSysReleaseComponent(GenericTable):
    __tablename__ = "opsysreleasescomponents"
    __table_args__ = (UniqueConstraint('opsysreleases_id', 'components_id'),)

    id = Column(Integer, primary_key=True)
    opsysreleases_id = Column(Integer, ForeignKey(f"{OpSysRelease.__tablename__}.id"),
                              nullable=False, index=True)
    components_id = Column(Integer, ForeignKey(f"{OpSysComponent.__tablename__}.id"),
                           nullable=False, index=True)

    release = relationship(OpSysRelease, backref="components")
    component = relationship(OpSysComponent, backref="releases")


class AssociatePeople(GenericTable):
    __tablename__ = "associatepeople"
    __table_args__ = (UniqueConstraint('name'),)

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, index=True)


class OpSysComponentAssociate(GenericTable):
    __tablename__ = "opsyscomponentsassociates"

    opsyscomponent_id = Column(Integer, ForeignKey(f"{OpSysComponent.__tablename__}.id"),
                               primary_key=True)
    associatepeople_id = Column(Integer, ForeignKey(f"{AssociatePeople.__tablename__}.id"),
                                primary_key=True)
    permission = Column(Enum("watchbugzilla", "commit", name="permission_type"), default="commit",
                        primary_key=True)

    component = relationship(OpSysComponent, backref="associates")
    associates = relationship(AssociatePeople, backref="components")


class Build(GenericTable):
    __tablename__ = "builds"

    id = Column(Integer, primary_key=True)
    base_package_name = Column(String(256), nullable=False, index=True)
    projrelease_id = Column(Integer, ForeignKey(f"{ProjRelease.__tablename__}.id"),
                            nullable=True, index=True)
    epoch = Column(Integer, nullable=False, index=True)
    version = Column(String(64), nullable=False, index=True)
    release = Column(String(64), nullable=False, index=True)
    semver = Column(Semver, nullable=False)  # semantic version
    semrel = Column(Semver, nullable=False)  # semantic release
    projrelease = relationship(ProjRelease)
    Index("ix_builds_semver_semrel", semver, semrel)

    def nvr(self) -> str:
        return f"{self.base_package_name}-{self.version}-{self.release}"

    def nevr(self) -> str:
        if not self.epoch:
            return self.nvr()
        return "{self.base_package_name}-{self.epoch}:{self.version}-{self.release}"

    @property
    def serialize(self) -> Dict[str, Union[int, str]]:
        return {
            'id': self.id,
            'base_package_name': self.base_package_name,
            'projrelease_id': self.projrelease_id,
            'epoch': self.epoch,
            'version': self.version,
            'release': self.release,
            'semver': self.semver,
            'semrel': self.semrel,
            'projrelease': self.projrelease,
            'nvr': self.nvr()
        }


class BuildOpSysReleaseArch(GenericTable):
    __tablename__ = "buildopsysreleasearch"

    build_id = Column(Integer, ForeignKey(f"{Build.__tablename__}.id"),
                      primary_key=True)
    opsysrelease_id = Column(Integer, ForeignKey(f"{OpSysRelease.__tablename__}.id"),
                             primary_key=True)
    arch_id = Column(Integer, ForeignKey(f"{Arch.__tablename__}.id"),
                     primary_key=True)

    build = relationship(Build)
    opsysrelease = relationship(OpSysRelease)
    arch = relationship(Arch)


class BuildArch(GenericTable):
    __tablename__ = "buildarchs"

    build_id = Column(Integer, ForeignKey(f"{Build.__tablename__}.id"),
                      primary_key=True)
    arch_id = Column(Integer, ForeignKey(f"{Arch.__tablename__}.id"),
                     primary_key=True)

    build = relationship(Build)
    arch = relationship(Arch)


class BuildComponent(GenericTable):
    __tablename__ = "buildcomponents"

    build_id = Column(Integer, ForeignKey(f"{Build.__tablename__}.id"),
                      nullable=False, primary_key=True)
    component_id = Column(Integer, ForeignKey(f"{OpSysComponent.__tablename__}.id"),
                          nullable=False, primary_key=True)

    build = relationship(Build, backref="components")
    component = relationship(OpSysComponent, backref="builds")


class Package(GenericTable):
    __tablename__ = "packages"
    __lobs__ = {"package": 1 << 31, "offset_map": 1 << 26}

    id = Column(Integer, primary_key=True)
    secondary_id = Column(Integer, nullable=True)
    build_id = Column(Integer, ForeignKey(f"{Build.__tablename__}.id"),
                      nullable=False, index=True)
    arch_id = Column(Integer, ForeignKey(f"{Arch.__tablename__}.id"),
                     nullable=False, index=True)
    name = Column(String(256), nullable=False, index=True)
    pkgtype = Column(Enum("rpm", "deb", "tgz", name="package_type"), nullable=True)
    build = relationship(Build, backref="packages")
    arch = relationship(Arch)

    #pylint:disable=E1103
    # Instance of 'RelationshipProperty' has no 'version' member
    def nvr(self) -> str:
        return f"{self.name}-{self.build.version}-{self.build.release}"

    def nvra(self) -> str:
        return f"{self.nvr()}.{self.arch.name}"

    def nevr(self) -> str:
        if not self.build.epoch:
            return self.nvr()
        return f"{self.name}-{self.build.epoch}:{self.build.version}-{self.build.release}"

    def nevra(self) -> str:
        return f"{self.nevr()}.{self.arch.name}"

    def filename(self) -> str:
        return f"{self.nvra()}.rpm"

    def evr(self) -> str:
        return f"{self.build.epoch}:{self.build.version}-{self.build.release}"

    def get_lob_extension(self) -> str:
        return f".{self.pkgtype}"

    def __str__(self) -> str:
        return self.nvra()


class PackageDependency(GenericTable):
    __tablename__ = "packagedependencies"

    id = Column(Integer, primary_key=True)
    package_id = Column(Integer, ForeignKey(f"{Package.__tablename__}.id"),
                        nullable=False, index=True)
    type = Column(Enum("PROVIDES", "REQUIRES", "CONFLICTS",
                       name="packagedependency_type"),
                  nullable=False, index=True)
    name = Column(String(1024), nullable=False, index=True)
    flags = Column(Integer, nullable=False)
    epoch = Column(Integer, nullable=True)
    version = Column(String(64), nullable=True)
    release = Column(String(64), nullable=True)
    package = relationship(Package, backref="dependencies")
