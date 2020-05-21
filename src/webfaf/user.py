# Copyright (C) 2018  ABRT Team
# Copyright (C) 2018  Red Hat, Inc.
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

from flask import Blueprint, flash, g, make_response, redirect, session
from werkzeug.wrappers import Response
from pyfaf import queries
from pyfaf.utils.user import UserDataDumper
from webfaf.webfaf_main import db, oid
from webfaf.utils import (create_anonymous_bzuser,
                          delete_bugzilla_user,
                          login_required)

user = Blueprint("user", __name__)


@user.route("/delete_data", endpoint='delete')
@login_required
def delete_user_data() -> Response:
    usermail = g.user.mail
    fas_user = queries.get_user_by_mail(db, usermail).first()
    bz_user = queries.get_bz_user(db, usermail)
    contact_email = queries.get_contact_email(db, usermail)

    if bz_user is not None:
        anonymous = create_anonymous_bzuser(db, uid=-1)
        delete_bugzilla_user(db, bz_user.id, anonymous.id)
        db.session.delete(bz_user)

    if fas_user is not None:
        queries.get_reportarchives_by_username(db, fas_user.username).delete(False)
        queries.get_problemreassigns_by_username(db, fas_user.username).delete(False)

    if contact_email is not None:
        queries.get_reportcontactmails_by_id(db, contact_email.id).delete(False)
        db.session.delete(contact_email)

    # Sign out user before deleting his account
    session.pop("openid", None)
    flash(u"You were signed out.", category='info')
    db.session.delete(fas_user)
    db.session.commit()

    return redirect(oid.get_next_url())


@user.route('/download_data', endpoint='download')
@login_required
def download_user_data() -> str:
    dumper = UserDataDumper(db, g.user.mail)
    resp = make_response(dumper.dump(pretty=True))
    resp.mimetype = 'application/json'
    resp.headers['Content-Disposition'] = 'attachment;filename=faf-{0}.json'\
                                          .format(g.user.username)
    return resp
