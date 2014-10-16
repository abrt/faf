import flask

from pyfaf.storage.user import User


login = flask.Blueprint("login", __name__)


from webfaf2 import db, oid
from utils import fed_raw_name


@login.route("/login/", methods=["GET"])
@oid.loginhandler
def do_login():
    if flask.g.user is not None:
        return flask.redirect(oid.get_next_url())
    else:
        return oid.try_login("https://id.fedoraproject.org/",
                             ask_for=["email"])


@oid.after_login
def create_or_login(resp):
    flask.session["openid"] = resp.identity_url
    username = fed_raw_name(resp.identity_url)

    user = db.session.query(User).filter(User.username == username).first()
    if not user:  # create
        user = User(username=username, mail=resp.email)
    else:
        user.mail = resp.email

    db.session.add(user)
    db.session.commit()
    flask.flash(u"Welcome, {0}".format(user.username))
    flask.g.user = user

    if flask.request.url_root == oid.get_next_url():
        return flask.redirect(flask.url_for("summary.index"))

    return flask.redirect(oid.get_next_url())


@login.route("/logout/")
def do_logout():
    flask.session.pop("openid", None)
    flask.flash(u"You were signed out")
    return flask.redirect(oid.get_next_url())
