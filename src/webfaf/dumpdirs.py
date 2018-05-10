import os
import re
import tarfile
import logging
import datetime
import sys

if sys.version_info.major == 2:
#Python 2
    from cStringIO import StringIO
else:
#Python 3
    from io import StringIO

from pyfaf.config import config, paths
from flask import (Blueprint, render_template, request, abort, redirect,
                   url_for, flash, jsonify)
from werkzeug import secure_filename
from werkzeug.wrappers import Response
from webfaf.utils import admin_required, InvalidUsage, request_wants_json


dumpdirs = Blueprint("dumpdirs", __name__)
logger = logging.getLogger("webfaf.dumpdirs")

from webfaf.forms import NewDumpDirForm


def check_filename(fn):
    """
    Check if filename matches format used by libreport:
        ccpp-2014-09-19-18:42:28-12810.tar.gz or
        Python3-2014-09-19-18:42:28-12810.tar.gz
    """

    return bool(
        re.match("[a-zA-Z]+\d?-\d{4}-\d{2}-\d{2}-\d{2}:\d{2}:\d{2}(-\d+)+.tar.gz", fn))


@dumpdirs.route("/")
@admin_required
def dashboard():
    dirs = ((datetime.datetime.fromtimestamp(os.path.getctime(full_path)),
             dir_entry,
             os.path.getsize(full_path))
            for dir_entry, full_path
            in map(lambda base_name:
                   (base_name, os.path.join(paths["dumpdir"], base_name)),
                   os.listdir(paths["dumpdir"])))

    dirs = sorted(dirs, key=lambda dentry: dentry[0])

    state = {
        "cachesizequota":  config["dumpdir.cachedirectorysizequota"],
        "cachesize":       sum((x[2] for x in dirs)),
        "cachecountquota": config["dumpdir.cachedirectorycountquota"],
        "cachecount":      len(dirs),
    }

    return render_template("dumpdirs/list.html",
                           dirs=dirs, state=state)


@dumpdirs.route("/download/<string:dirname>")
@admin_required
def item(dirname):
    if dirname == "all":
        items = os.listdir(paths["dumpdir"])
    else:
        items = dirname.split(",")

    if len(items) == 1:
        item = items[0]
        archive_path = os.path.join(paths["dumpdir"], item)

        if not os.path.isfile(archive_path):
            abort(404)

        archive = open(archive_path)
        archive_size = os.path.getsize(archive_path)

        return Response(archive, content_type="application/octet-stream",
                        headers={"Content-length": archive_size},
                        direct_passthrough=True)

    else:  # tar multiple files
        c = StringIO()
        tarred = tarfile.open(fileobj=c, mode='w')
        for item in items:
            archive_path = os.path.join(paths["dumpdir"], item)

            if not os.path.isfile(archive_path):
                abort(404)

            tarred.add(archive_path, arcname=item)
        tarred.close()

        cd = "attachment; filename=fafdds-{0}.tar.gz".format(
            datetime.datetime.now().isoformat())

        return Response(c, content_type="application/octet-stream",
                        headers={"Content-length": c.tell(),
                                 "Content-Disposition": cd},
                        direct_passthrough=True)


@dumpdirs.route("/new/", methods=("GET", "POST", "PUT"))
@dumpdirs.route("/new/<string:url_fname>/", methods=("GET", "POST", "PUT"))
def new(url_fname=None):
    """
    Handle dump dir archive uploads
    """

    form = NewDumpDirForm()
    if request.method in ["POST", "PUT"]:
        try:
            if request.method == "POST":
                if not form.validate() or form.file.name not in request.files:
                    raise InvalidUsage("Invalid form data.", 400)

                archive_file = request.files[form.file.name]
                archive_fname = archive_file.filename

            if request.method == "PUT":
                archive_file = StringIO(request.stream.read())
                archive_fname = url_fname

            archive_file.seek(0, os.SEEK_END)
            archive_size = archive_file.tell()
            archive_file.seek(0)

            if not archive_size:
                raise InvalidUsage("Empty archive received", 400)

            if not check_filename(archive_fname):
                raise InvalidUsage("Wrong archive file name", 400)

            # sanitize input filename just to be sure
            archive_fname = secure_filename(archive_fname)

            if not os.path.exists(paths["dumpdir"]):
                raise InvalidUsage("That's embarrassing! We have some troubles"
                                   " with deployment. Please try again later.",
                                   500)

            count = 0
            try:
                count = sum(
                    1 for x in os.listdir(paths["dumpdir"])
                    if os.path.isfile(os.path.join(paths["dumpdir"], x)))

            except Exception as e:
                raise InvalidUsage("That's embarrassing! We have some troubles"
                                   " with storage. Please try again later.",
                                   500)

            if count >= int(config["dumpdir.cachedirectorycountquota"]):
                raise InvalidUsage("That's embarrassing! We have reached"
                                   " the limit of uploaded archives."
                                   " Please try again later.",
                                   500)

            if archive_size > int(config["dumpdir.maxdumpdirsize"]):
                raise InvalidUsage("Dump dir archive is too large", 413)

            used_space = 0.0
            try:
                used_space = sum(
                    float(os.path.getsize(x))
                    for x in map(lambda f: os.path.join(paths["dumpdir"], f),
                                 os.listdir(paths["dumpdir"]))
                    if os.path.isfile(x))
            except Exception as e:
                raise InvalidUsage("That's embarrasing! We have some"
                                   " troubles with disk space."
                                   " Please try again later.",
                                   500)

            quota = int(config["dumpdir.cachedirectorysizequota"])
            if (quota - archive_size) < used_space:
                raise InvalidUsage("That's embarrassing! We ran out"
                                   " of disk space."
                                   " Please try again later.",
                                   500)

            fpath = os.path.join(paths["dumpdir"], archive_fname)

            if os.path.exists(fpath):
                raise InvalidUsage("Dump dir archive already exists.", 409)

            with open(fpath, 'w') as dest:
                dest.write(archive_file.read())

            if request_wants_json():
                response = jsonify({"ok": "ok"})
                response.status_code = 201
                return response
            else:
                flash("Uploaded successfully.")
                return render_template("dumpdirs/new.html",
                                       form=form)

        except InvalidUsage as e:
            if e.status_code == 500:
                logger.error(e.message)
            elif e.status_code >= 400:
                logger.warning(e.message)

            if request_wants_json():
                response = jsonify({"error": e.message})
                response.status_code = e.status_code
                return response
            else:
                flash(e.message, "danger")
                return render_template("dumpdirs/new.html",
                                       form=form), e.status_code

    return render_template("dumpdirs/new.html",
                           form=form)


@dumpdirs.route("/delete/<string:dirname>/", methods=("GET", "POST"))
@admin_required
def delete(dirname):
    if dirname == "all":
        items = os.listdir(paths["dumpdir"])
    else:
        items = dirname.split(",")

    for item in items:
        archive_path = os.path.join(paths["dumpdir"], item)

        if not os.path.isfile(archive_path):
            abort(404)

        try:
            os.remove(archive_path)
        except OSError as e:
            logger.exception(e)
            return Response("Can't delete dump directory", status=500)

    return redirect(url_for("dumpdirs.dashboard"))
