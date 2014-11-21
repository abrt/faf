import os
import logging
from logging.handlers import SMTPHandler

import flask
from flask import Flask
from flask.ext.rstpages import RSTPages
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug.contrib.fixers import ProxyFix

from pyfaf.storage.user import User

app = Flask(__name__)

if "WEBFAF_ENVIRON_PRODUCTION" in os.environ:
    app.config.from_object('config.ProductionConfig')
elif "WEBFAF_ENVIRON_TEST" in os.environ:
    app.config.from_object('config.TestingConfig')
else:
    app.config.from_object('config.DevelopmentConfig')

db = SQLAlchemy(app)

if app.config["PROXY_SETUP"]:
    app.wsgi_app = ProxyFix(app.wsgi_app)

if app.config["OPENID_ENABLED"]:
    from flask.ext.openid import OpenID
    oid = OpenID(app, safe_roots=[])
    from login import login
    app.register_blueprint(login)

from dumpdirs import dumpdirs
app.register_blueprint(dumpdirs, url_prefix="/dumpdirs")
from reports import reports
app.register_blueprint(reports, url_prefix="/reports")
from problems import problems
app.register_blueprint(problems, url_prefix="/problems")
from stats import stats
app.register_blueprint(stats, url_prefix="/stats")
from summary import summary
app.register_blueprint(summary, url_prefix="/summary")

# Import plugin blueprints
for filename in os.listdir(os.path.dirname(__file__)+"/blueprints"):
    if not filename.endswith(".py"):
        continue
    if filename.startswith("_"):
        continue

    plugin = "{0}.{1}".format("blueprints", filename[:-3])

    try:
        blueprint = getattr(__import__(plugin), filename[:-3])
        app.register_blueprint(blueprint.blueprint,
                               url_prefix=blueprint.url_prefix)
    except Exception as ex:
        logging.exception("Error importing {0} blueprint.".format(filename))

from filters import problem_label, fancydate, timestamp
app.jinja_env.filters['problem_label'] = problem_label
app.jinja_env.filters['fancydate'] = fancydate
app.jinja_env.filters['timestamp'] = timestamp

from utils import cache, fed_raw_name, WebfafJSONEncoder
app.json_encoder = WebfafJSONEncoder


@app.route('/')
def hello_world():
    return flask.redirect(flask.url_for("summary.index"), code=302)


@app.route('/about')
@cache(hours=24)
def about():
    rstdoc = RSTPages().get("about")
    return flask.render_template("rstpage.html", rstdoc=rstdoc)


@app.before_request
def before_request():
    flask.g.user = None
    if "openid" in flask.session:
        username = fed_raw_name(flask.session["openid"])
        flask.g.user = (db.session.query(User)
                        .filter(User.username == username)
                        .first())


if not app.debug:
    credentials = None
    if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
        credentials = (app.config['MAIL_USERNAME'],
                       app.config['MAIL_PASSWORD'])

    mail_handler = SMTPHandler(
        (app.config['MAIL_SERVER'],
         app.config['MAIL_PORT']),
        'no-reply@' + app.config['MAIL_SERVER'],
        app.config['ADMINS'],
        'webfaf exception', credentials)

    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)


@app.errorhandler(403)
def forbidden(error):
    return flask.render_template("403.html"), 403


@app.errorhandler(404)
def not_found(error):
    return flask.render_template("404.html"), 404


@app.errorhandler(413)
def request_entity_too_large(error):
    return flask.render_template("413.html"), 413


@app.errorhandler(500)
def panic(error):
    return flask.render_template("500.html"), 500


if __name__ == '__main__':
    app.run()
