import os
import logging
from logging.handlers import SMTPHandler

from ratelimitingfilter import RateLimitingFilter

import flask
import json
import bunch
from flask import Flask, Response, current_app
from flask_rstpages import RSTPages
from flask_sqlalchemy import SQLAlchemy
from werkzeug.contrib.fixers import ProxyFix
from werkzeug.local import LocalProxy

from pyfaf.storage.user import User
from pyfaf.storage import OpSysComponent, Report
from sqlalchemy import distinct

app = Flask(__name__)

if "WEBFAF_ENVIRON_PRODUCTION" in os.environ:
    app.config.from_object("webfaf.config.ProductionConfig")
elif "WEBFAF_ENVIRON_TEST" in os.environ:
    app.config.from_object("webfaf.config.TestingConfig")
else:
    app.config.from_object("webfaf.config.DevelopmentConfig")

db = SQLAlchemy(app)

if app.config["CACHE_TYPE"].lower() == "memcached":
    from werkzeug.contrib.cache import MemcachedCache
    flask_cache = MemcachedCache(['{0}:{1}'.format(
        app.config["MEMCACHED_HOST"],
        app.config["MEMCACHED_PORT"])],
                                 key_prefix=app.config["MEMCACHED_KEY_PREFIX"])
elif app.config["CACHE_TYPE"].lower() == "simple":
    from werkzeug.contrib.cache import SimpleCache
    flask_cache = SimpleCache()
else:
    from werkzeug.contrib.cache import NullCache
    flask_cache = NullCache()

if app.config["PROXY_SETUP"]:
    app.wsgi_app = ProxyFix(app.wsgi_app)

if app.config["OPENID_ENABLED"]:
    from flask_openid import OpenID
    from openid_teams import teams
    oid = OpenID(app, safe_roots=[], extension_responses=[teams.TeamsResponse])
    from webfaf.login import login
    app.register_blueprint(login)

from webfaf.dumpdirs import dumpdirs
app.register_blueprint(dumpdirs, url_prefix="/dumpdirs")
from webfaf.reports import reports
app.register_blueprint(reports, url_prefix="/reports")
from webfaf.problems import problems
app.register_blueprint(problems, url_prefix="/problems")
from webfaf.stats import stats
app.register_blueprint(stats, url_prefix="/stats")
from webfaf.summary import summary
app.register_blueprint(summary, url_prefix="/summary")


def import_blueprint_plugins(app):
    menu_public = []
    menu_admin = []
    blueprints_path = os.path.join(os.path.dirname(__file__), "blueprints")

    for filename in os.listdir(blueprints_path):
        if not filename.endswith(".py"):
            continue
        if filename.startswith("_"):
            continue

        plugin = "{0}.{1}".format("blueprints", filename[:-3])

        try:
            imp = __import__(plugin)
            blueprint = getattr(imp, filename[:-3])
            app.register_blueprint(blueprint.blueprint,
                                   url_prefix=blueprint.url_prefix)
            if hasattr(blueprint, "blueprint_menu"):
                for menu_item in blueprint.blueprint_menu:
                    if menu_item.get("admin_required"):
                        menu_admin.append(menu_item)
                    else:
                        menu_public.append(menu_item)
        except Exception as ex:
            logging.exception("Error importing {0} blueprint.".format(filename))
            raise ex

    # This is the official Flask way to store extra data to the app
    if not hasattr(app, "extensions"):
        app.extensions = {}
    app.extensions["menu"] = {
        "public": menu_public,
        "admin": menu_admin
    }

# Add current_menu to teplates. Need some fiddling with app context.
app.context_processor(lambda: dict(
    current_menu=LocalProxy(lambda: current_app.extensions.get(
        "menu", {"public": [], "admin": []}))))

from webfaf.filters import (problem_label, fancydate, timestamp, memory_address,
                            readable_int)
app.jinja_env.filters['problem_label'] = problem_label
app.jinja_env.filters['fancydate'] = fancydate
app.jinja_env.filters['timestamp'] = timestamp
app.jinja_env.filters['memory_address'] = memory_address
app.jinja_env.filters['readable_int'] = readable_int

from webfaf.utils import cache, fed_raw_name, WebfafJSONEncoder
app.json_encoder = WebfafJSONEncoder


@app.route('/')
def root():
    return flask.redirect(flask.url_for("summary.index"), code=302)


@app.route('/about')
@cache(hours=24)
def about():
    rstdoc = RSTPages().get("about")
    return flask.render_template("rstpage.html", rstdoc=rstdoc)


@app.route('/component_names.json')
@cache(hours=24)
def component_names_json():
    sub = db.session.query(distinct(Report.component_id)).subquery()
    comps = (db.session.query(OpSysComponent.name)
             .filter(OpSysComponent.id.in_(sub))
             .distinct(OpSysComponent.name)
             .all())
    comps = [comp[0] for comp in comps]
    return Response(response=json.dumps(comps),
                    status=200,
                    mimetype="application/json")


@app.before_request
def before_request():
    flask.g.user = None
    if "openid" in flask.session:
        username = fed_raw_name(flask.session["openid"])
        flask.g.user = (db.session.query(User)
                        .filter(User.username == username)
                        .first())

    elif app.config["EVERYONE_IS_ADMIN"]:
        flask.g.user = bunch.Bunch({
            "username": "admin",
            "email": "admin@localhost",
            "admin": True
        })


if not app.debug:
    credentials = None
    if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
        credentials = (app.config['MAIL_USERNAME'],
                       app.config['MAIL_PASSWORD'])

    mail_handler = SMTPHandler(
        (app.config['MAIL_SERVER'],
         app.config['MAIL_PORT']),
        app.config['MAIL_FROM'],
        app.config['ADMINS'],
        'webfaf exception', credentials)

    mail_handler.setLevel(logging.ERROR)
    rate_limiter = RateLimitingFilter(app.config['THROTTLING_RATE'],
                                      app.config['THROTTLING_TIMEFRAME'],
                                      app.config['THROTTLING_BURST'])

    mail_handler.addFilter(rate_limiter)
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
    import_blueprint_plugins(app)
    app.run()
