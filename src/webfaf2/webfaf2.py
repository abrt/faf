import os

from flask.ext.sqlalchemy import SQLAlchemy
from flask import Flask, redirect

app = Flask(__name__)

if "WEBFAF_ENVIRON_PRODUCTION" in os.environ:
    app.config.from_object('config.ProductionConfig')
elif "WEBFAF_ENVIRON_TEST" in os.environ:
    app.config.from_object('config.TestingConfig')
else:
    app.config.from_object('config.DevelopmentConfig')

db = SQLAlchemy(app)

from reports import reports
app.register_blueprint(reports, url_prefix="/reports")
from problems import problems
app.register_blueprint(problems, url_prefix="/problems")
from summary import summary
app.register_blueprint(summary, url_prefix="/summary")

from filters import problem_label, fancydate, timestamp
app.jinja_env.filters['problem_label'] = problem_label
app.jinja_env.filters['fancydate'] = fancydate
app.jinja_env.filters['timestamp'] = timestamp


@app.route('/')
def hello_world():
    return redirect("/summary/", code=302)

if __name__ == '__main__':
    app.run()
