from flask import abort, Blueprint, flash, g, redirect, session, url_for
from pyfaf import queries
from webfaf.webfaf_main import db, oid
from webfaf.utils import (delete_complete_report,
                          delete_user_bugzillas,
                          login_required)

user = Blueprint("user", __name__)


@user.route("/delete_data", endpoint='delete')
@login_required
def delete_user_data():
    usermail = g.user.mail
    fas_user = queries.get_user_by_mail(db, usermail).first()
    bz_user = queries.get_bz_user(db, usermail)
    contact_email = queries.get_contact_email(db, usermail)

    if bz_user is not None:
        delete_user_bugzillas(db, bz_user.id)
        db.session.delete(bz_user)

    if fas_user is not None:
        queries.get_reportarchives_by_username(db, fas_user.username).delete(False)
        queries.get_problemreassigns_by_username(db, fas_user.username).delete(False)

    if contact_email is not None:
        user_reports = queries.get_reportcontactmails_by_id(db, contact_email.id)

        for report in user_reports.all():
            delete_complete_report(db, report.report_id)

        user_reports.delete(False)
        db.session.delete(contact_email)

    # Sign out user before deleting his account
    session.pop("openid", None)
    flash(u"You were signed out.", category='info')
    db.session.delete(fas_user)
    db.session.commit()

    return redirect(oid.get_next_url())


@user.route('/download_data', endpoint='download')
def download_user_data():
    return redirect(url_for('summary.index'))
