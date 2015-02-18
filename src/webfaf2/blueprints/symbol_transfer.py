from hashlib import sha1
import datetime
from sqlalchemy import func

from flask import Blueprint, request, jsonify
from pyfaf.storage import (OpSysComponent,
                           Report,
                           ReportBacktrace,
                           ReportBtThread,
                           ReportBtFrame,
                           ReportHash,
                           SymbolSource)
from pyfaf.config import config
from pyfaf.queries import get_report_by_hash
from webfaf2_main import db


url_prefix = "/symbol_transfer"

symbol_transfer = Blueprint("symbol_transfer", __name__)

symbol_transfer_auth_key = config.get("symbol_transfer.auth_key", False)


@symbol_transfer.route("/get_symbol/")
def get_symbol():
    # required GET params
    build_id = request.args.get("build_id", "")
    path = request.args.get("path", "")
    offset = int(request.args.get("offset", 0))

    # required when creating symbol for retracing later
    problem_type = request.args.get("type", "")
    create_symbol_auth_key = request.args.get("create_symbol_auth", False)

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

            r = jsonify({"error": "SymbolSource not found but created. Please wait."})
            r.status_code = 202
            return r

        else:
            r = jsonify({"error": "SymbolSource not found"})
            r.status_code = 404
            return r

    if db_ssource.line_number is None:
        r = jsonify({"error": "SymbolSource not yet retraced. Please wait."})
        r.status_code = 404
        return r

    return jsonify({
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
    })


blueprint = symbol_transfer
