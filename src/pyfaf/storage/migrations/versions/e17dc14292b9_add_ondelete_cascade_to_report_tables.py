# Copyright (C) 2016  ABRT Team
# Copyright (C) 2016  Red Hat, Inc.
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

"""
Add ondelete cascade to report tables

Revision ID: e17dc14292b9
Revises: cb084388e232
Create Date: 2019-03-21 12:42:03.773304
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e17dc14292b9'
down_revision = 'cb084388e232'


def upgrade():
    op.drop_constraint('reportarchive_report_id_fkey', 'reportarchive', type_='foreignkey')
    op.create_foreign_key('reportarchive_report_id_fkey', 'reportarchive', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportarchs_report_id_fkey', 'reportarchs', type_='foreignkey')
    op.create_foreign_key('reportarchs_report_id_fkey', 'reportarchs', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportbacktraces_report_id_fkey', 'reportbacktraces', type_='foreignkey')
    op.create_foreign_key('reportbacktraces_report_id_fkey', 'reportbacktraces', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportbz_report_id_fkey', 'reportbz', type_='foreignkey')
    op.create_foreign_key('reportbz_report_id_fkey', 'reportbz', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportcomments_report_id_fkey', 'reportcomments', type_='foreignkey')
    op.create_foreign_key('reportcomments_report_id_fkey', 'reportcomments', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportcontactemails_report_id_fkey', 'reportcontactemails', type_='foreignkey')
    op.create_foreign_key('reportcontactemails_report_id_fkey', 'reportcontactemails', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportexecutables_report_id_fkey', 'reportexecutables', type_='foreignkey')
    op.create_foreign_key('reportexecutables_report_id_fkey', 'reportexecutables', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportexternalfaf_report_id_fkey', 'reportexternalfaf', type_='foreignkey')
    op.create_foreign_key('reportexternalfaf_report_id_fkey', 'reportexternalfaf', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reporthashes_report_id_fkey', 'reporthashes', type_='foreignkey')
    op.create_foreign_key('reporthashes_report_id_fkey', 'reporthashes', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reporthistorydaily_report_id_fkey', 'reporthistorydaily', type_='foreignkey')
    op.create_foreign_key('reporthistorydaily_report_id_fkey', 'reporthistorydaily', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reporthistorymonthly_report_id_fkey', 'reporthistorymonthly', type_='foreignkey')
    op.create_foreign_key('reporthistorymonthly_report_id_fkey', 'reporthistorymonthly', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reporthistoryweekly_report_id_fkey', 'reporthistoryweekly', type_='foreignkey')
    op.create_foreign_key('reporthistoryweekly_report_id_fkey', 'reporthistoryweekly', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportmantis_report_id_fkey', 'reportmantis', type_='foreignkey')
    op.create_foreign_key('reportmantis_report_id_fkey', 'reportmantis', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportopsysreleases_report_id_fkey', 'reportopsysreleases', type_='foreignkey')
    op.create_foreign_key('reportopsysreleases_report_id_fkey', 'reportopsysreleases', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportpackages_report_id_fkey', 'reportpackages', type_='foreignkey')
    op.create_foreign_key('reportpackages_report_id_fkey', 'reportpackages', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportraw_report_id_fkey', 'reportraw', type_='foreignkey')
    op.create_foreign_key('reportraw_report_id_fkey', 'reportraw', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportreasons_report_id_fkey', 'reportreasons', type_='foreignkey')
    op.create_foreign_key('reportreasons_report_id_fkey', 'reportreasons', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportreleasedesktops_report_id_fkey', 'reportreleasedesktops', type_='foreignkey')
    op.create_foreign_key('reportreleasedesktops_report_id_fkey', 'reportreleasedesktops', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportselinuxcontexts_report_id_fkey', 'reportselinuxcontexts', type_='foreignkey')
    op.create_foreign_key('reportselinuxcontexts_report_id_fkey', 'reportselinuxcontexts', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportselinuxmodes_report_id_fkey', 'reportselinuxmodes', type_='foreignkey')
    op.create_foreign_key('reportselinuxmodes_report_id_fkey', 'reportselinuxmodes', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportunknownpackages_report_id_fkey', 'reportunknownpackages', type_='foreignkey')
    op.create_foreign_key('reportunknownpackages_report_id_fkey', 'reportunknownpackages', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reportuptimes_report_id_fkey', 'reportuptimes', type_='foreignkey')
    op.create_foreign_key('reportuptimes_report_id_fkey', 'reportuptimes', 'reports', ['report_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('reporturls_report_id_fkey', 'reporturls', type_='foreignkey')
    op.create_foreign_key('reporturls_report_id_fkey', 'reporturls', 'reports', ['report_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint('reporturls_report_id_fkey', 'reporturls', type_='foreignkey')
    op.create_foreign_key('reporturls_report_id_fkey', 'reporturls', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportuptimes_report_id_fkey', 'reportuptimes', type_='foreignkey')
    op.create_foreign_key('reportuptimes_report_id_fkey', 'reportuptimes', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportunknownpackages_report_id_fkey', 'reportunknownpackages', type_='foreignkey')
    op.create_foreign_key('reportunknownpackages_report_id_fkey', 'reportunknownpackages', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportselinuxmodes_report_id_fkey', 'reportselinuxmodes', type_='foreignkey')
    op.create_foreign_key('reportselinuxmodes_report_id_fkey', 'reportselinuxmodes', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportselinuxcontexts_report_id_fkey', 'reportselinuxcontexts', type_='foreignkey')
    op.create_foreign_key('reportselinuxcontexts_report_id_fkey', 'reportselinuxcontexts', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportreleasedesktops_report_id_fkey', 'reportreleasedesktops', type_='foreignkey')
    op.create_foreign_key('reportreleasedesktops_report_id_fkey', 'reportreleasedesktops', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportreasons_report_id_fkey', 'reportreasons', type_='foreignkey')
    op.create_foreign_key('reportreasons_report_id_fkey', 'reportreasons', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportraw_report_id_fkey', 'reportraw', type_='foreignkey')
    op.create_foreign_key('reportraw_report_id_fkey', 'reportraw', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportpackages_report_id_fkey', 'reportpackages', type_='foreignkey')
    op.create_foreign_key('reportpackages_report_id_fkey', 'reportpackages', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportopsysreleases_report_id_fkey', 'reportopsysreleases', type_='foreignkey')
    op.create_foreign_key('reportopsysreleases_report_id_fkey', 'reportopsysreleases', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportmantis_report_id_fkey', 'reportmantis', type_='foreignkey')
    op.create_foreign_key('reportmantis_report_id_fkey', 'reportmantis', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reporthistoryweekly_report_id_fkey', 'reporthistoryweekly', type_='foreignkey')
    op.create_foreign_key('reporthistoryweekly_report_id_fkey', 'reporthistoryweekly', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reporthistorymonthly_report_id_fkey', 'reporthistorymonthly', type_='foreignkey')
    op.create_foreign_key('reporthistorymonthly_report_id_fkey', 'reporthistorymonthly', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reporthistorydaily_report_id_fkey', 'reporthistorydaily', type_='foreignkey')
    op.create_foreign_key('reporthistorydaily_report_id_fkey', 'reporthistorydaily', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reporthashes_report_id_fkey', 'reporthashes', type_='foreignkey')
    op.create_foreign_key('reporthashes_report_id_fkey', 'reporthashes', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportexternalfaf_report_id_fkey', 'reportexternalfaf', type_='foreignkey')
    op.create_foreign_key('reportexternalfaf_report_id_fkey', 'reportexternalfaf', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportexecutables_report_id_fkey', 'reportexecutables', type_='foreignkey')
    op.create_foreign_key('reportexecutables_report_id_fkey', 'reportexecutables', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportcontactemails_report_id_fkey', 'reportcontactemails', type_='foreignkey')
    op.create_foreign_key('reportcontactemails_report_id_fkey', 'reportcontactemails', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportcomments_report_id_fkey', 'reportcomments', type_='foreignkey')
    op.create_foreign_key('reportcomments_report_id_fkey', 'reportcomments', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportbz_report_id_fkey', 'reportbz', type_='foreignkey')
    op.create_foreign_key('reportbz_report_id_fkey', 'reportbz', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportbacktraces_report_id_fkey', 'reportbacktraces', type_='foreignkey')
    op.create_foreign_key('reportbacktraces_report_id_fkey', 'reportbacktraces', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportarchs_report_id_fkey', 'reportarchs', type_='foreignkey')
    op.create_foreign_key('reportarchs_report_id_fkey', 'reportarchs', 'reports', ['report_id'], ['id'])

    op.drop_constraint('reportarchive_report_id_fkey', 'reportarchive', type_='foreignkey')
    op.create_foreign_key('reportarchive_report_id_fkey', 'reportarchive', 'reports', ['report_id'], ['id'])
