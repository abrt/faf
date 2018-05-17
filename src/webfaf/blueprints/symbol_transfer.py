from hashlib import sha1
import datetime
import json
from sqlalchemy import func

from flask import Blueprint, request, jsonify, abort, Response
from pyfaf.storage import (OpSysComponent,
                           Report,
                           ReportBacktrace,
                           ReportBtThread,
                           ReportBtFrame,
                           ReportHash,
                           SymbolSource)
from pyfaf.config import config
from webfaf_main import db


url_prefix = "/symbol_transfer"

symbol_transfer = Blueprint("symbol_transfer", __name__)

symbol_transfer_auth_key = config.get("symbol_transfer.auth_key", False)


def process_symbol(build_id, path, offset, problem_type, create_symbol_auth_key):
    db_ssource = (db.session.query(SymbolSource)
                  .filter(SymbolSource.build_id == build_id)
                  .filter(SymbolSource.path == path)
                  .filter(SymbolSource.offset == offset)
                  .first())
    if db_ssource is None:
        if (create_symbol_auth_key
                and symbol_transfer_auth_key
                and create_symbol_auth_key == symbol_transfer_auth_key
                and problem_type in ("kerneloops", "core")):

            # We need to attach our symbols to a dummy report in order to set
            # their type
            h = sha1()
            h.update("symbol_transfer_dummy")
            h.update(problem_type)
            dummy_report_hash = h.hexdigest()
            # The thread all our frames and symbols are going to be attached to
            db_thread = (db.session.query(ReportBtThread)
                         .join(ReportBacktrace)
                         .join(Report)
                         .join(ReportHash)
                         .filter(ReportHash.hash == dummy_report_hash)
                         .first())
            if db_thread is None:
                # Need to potentially create the whole chain of objects
                db_report = (db.session.query(Report)
                             .join(ReportHash)
                             .filter(ReportHash.hash == dummy_report_hash)
                             .first())
                if db_report is None:
                    db_report = Report()
                    db_report.type = problem_type
                    db_report.first_occurence = datetime.datetime.fromtimestamp(0)
                    db_report.last_occurence = db_report.first_occurence
                    db_report.count = 0
                    # Random component
                    db_report.component = db.session.query(OpSysComponent).first()
                    db.session.add(db_report)

                    db_report_hash = ReportHash()
                    db_report_hash.hash = dummy_report_hash
                    db_report_hash.report = db_report
                    db.session.add(db_report_hash)

                db_rbt = (db.session.query(ReportBacktrace)
                          .filter(ReportBacktrace.report == db_report)
                          .first())
                if db_rbt is None:
                    db_rbt = ReportBacktrace()
                    db_rbt.report = db_report
                    db_rbt.quality = -1000
                    db.session.add(db_rbt)

                db_thread = ReportBtThread()
                db_thread.backtrace = db_rbt
                # This prevents this dummy thread from being clustered
                db_thread.crashthread = False
                db.session.add(db_thread)

            db_ssource = SymbolSource()
            db_ssource.build_id = build_id
            db_ssource.path = path
            db_ssource.offset = offset
            db.session.add(db_ssource)

            max_order = (db.session.query(func.max(ReportBtFrame.order))
                         .filter(ReportBtFrame.thread == db_thread)
                         .scalar() or 0)
            db_frame = ReportBtFrame()
            db_frame.thread = db_thread
            db_frame.symbolsource = db_ssource
            db_frame.order = max_order + 1
            db.session.add(db_frame)

            db.session.commit()

            return {"error": "SymbolSource not found but created. Please wait."}, 202

        else:
            return {"error": "SymbolSource not found"}, 404

    if db_ssource.line_number is None:
        return {"error": "SymbolSource not yet retraced. Please wait."}, 404

    return {
        "Symbol": {
            "name": db_ssource.symbol.name,
            "nice_name": db_ssource.symbol.nice_name,
            "normalized_path": db_ssource.symbol.normalized_path,
        },
        "SymbolSource": {
            "build_id": db_ssource.build_id,
            "path": db_ssource.path,
            "offset": db_ssource.offset,
            "func_offset": db_ssource.func_offset,
            "hash": db_ssource.hash,
            "source_path": db_ssource.source_path,
            "line_number": db_ssource.line_number,
        }
    }, 200


@symbol_transfer.route("/get_symbol/", methods=("GET", "POST"))
def get_symbol():
    create_symbol_auth_key = request.args.get("create_symbol_auth", False)
    if request.method == "GET":
        # required GET params
        build_id = request.args.get("build_id", "")
        path = request.args.get("path", "")
        offset = int(request.args.get("offset", 0))

        # required when creating symbol for retracing later
        problem_type = request.args.get("type", "")

        result, status_code = process_symbol(build_id, path, offset,
                                             problem_type,
                                             create_symbol_auth_key)

        r = jsonify(result)
        r.status_code = status_code
        return r

    # POST
    if not request.json:
        abort(400)

    r = []
    for req in request.json:
        build_id = req.get("build_id", "")
        path = req.get("path", "")
        offset = int(req.get("offset", 0))

        # required when creating symbol for retracing later
        problem_type = req.get("type", "")

        result, status_code = process_symbol(build_id, path, offset,
                                             problem_type,
                                             create_symbol_auth_key)
        r.append(result)

    return Response(
        response=json.dumps(r),
        status=200,
        mimetype="application/json")


blueprint = symbol_transfer
