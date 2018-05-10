import flask
from openid_teams import teams

from pyfaf.storage.user import User


login = flask.Blueprint("login", __name__)


from webfaf.webfaf_main import db, oid, app
from webfaf.utils import fed_raw_name


@login.route("/login/", methods=["GET"])
@oid.loginhandler
def do_login():
    if flask.g.user is not None:
        return flask.redirect(oid.get_next_url())
    else:
        teams_req = teams.TeamsRequest(app.config["OPENID_PRIVILEGED_TEAMS"])
        return oid.try_login("https://id.fedoraproject.org/",
                             ask_for=["email"], extensions=[teams_req])


@oid.after_login
def create_or_login(resp):
    flask.session["openid"] = resp.identity_url
    username = fed_raw_name(resp.identity_url)

    privileged = False
    # "lp" is the namespace for openid-teams
    if "lp" in resp.extensions and any(group in app.config["OPENID_PRIVILEGED_TEAMS"]
                                       for group in resp.extensions["lp"].teams):
        privileged = True

    user = db.session.query(User).filter(User.username == username).first()
    if not user:  # create
        user = User(username=username, mail=resp.email, privileged=privileged)
    else:
        user.mail = resp.email
        user.privileged = privileged

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
