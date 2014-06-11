# Copyright (C) 2014  ABRT Team
# Copyright (C) 2014  Red Hat, Inc.
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

import krbV


def kinit(principal_name, keytab_filename):
    context = krbV.default_context()
    ccache = context.default_ccache()
    principal = krbV.Principal(name=principal_name, context=context)
    ccache.init(principal)
    keytab = krbV.Keytab(keytab_filename, context=context)
    ccache.init_creds_keytab(keytab=keytab, principal=principal)
