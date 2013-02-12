import logging
import datetime

from storage.opsys import (OpSys,
                           OpSysRelease,
                           OpSysComponent)

from storage.rhbz import (RhbzBug,
                          RhbzUser,
                          RhbzBugCc,
                          RhbzComment,
                          RhbzAttachment,
                          RhbzBugHistory)

COMMENT_TYPES = ["NORMAL", "DUPLICATE_OF", "HAS_DUPLICATE", "POPULAR_VOTES", "MOVED_TO", "NEW_ATTACHMENT", "COMMENT_ON_ATTACHMENT"]

class Bugzilla:
    def __init__(self, db):
        self.db = db

    def user_exists_in_storage(self, user_id):
        if self.db is None:
            raise Exception, "Storage was not initialized"
        user = self.db.session.query(RhbzUser).filter(RhbzUser.id == user_id).first()
        return not user is None

    def download_user_to_storage(self, user_id, flush=False):
        if self.db is None:
            raise Exception, "Storage was not initialized"

        logging.debug("Downloading user #{0}".format(user_id))

        fields = ["id", "email", "name", "real_name", "can_login"]
        response = self.proxy.User.get({"ids": [user_id], "include_fields": fields})
        user = response["users"][0]

        result = RhbzUser()
        result.id = user["id"]
        result.email = user["email"]
        result.name = user["name"]
        result.real_name = user["real_name"]
        result.can_login = user["can_login"]

        self.db.session.add(result)
        if flush:
            self.db.session.flush()

        return result

    def bug_exists_in_storage(self, bug_id):
        if self.db is None:
            raise Exception, "Storage was not initialized"
        bug = self.db.session.query(RhbzBug).filter(RhbzBug.id == bug_id).first()
        return not bug is None

    def download_bug_to_storage(self, bug_id, with_comments=False, with_attachments=False, flush=False):
        if self.db is None:
            raise Exception, "Storage was not initialized"

        logging.debug("Downloading bug #{0}".format(bug_id))
        response = self.proxy.bugzilla.getBug(bug_id)
        times = self.proxy.Bug.get({"ids": [bug_id], "include_fields": ["creation_time", "last_change_time"]})
        history = self.proxy.Bug.history({"ids":[bug_id]})["bugs"][0]["history"]

        opsysrelease = self.db.session.query(OpSysRelease) \
                                      .join(OpSys) \
                                      .filter((OpSys.name == response["product"]) &
                                              (OpSysRelease.version == response["version"][0])) \
                                      .first()
        if not opsysrelease:
            logging.error("Unable to find release '{0} {1}'".format(response["product"], response["version"]))
            return None

        component = self.db.session.query(OpSysComponent) \
                                   .join(OpSys) \
                                   .filter((OpSys.id == opsysrelease.opsys.id) &
                                           (OpSysComponent.name == response["component"][0])) \
                                   .first()
        if not component:
            logging.error("Unable to find component '{0}' in '{1}'".format(response["component"][0], response["product"]))
            return None

        if not self.user_exists_in_storage(response["reporter_id"]):
            logging.debug("Creator #{0} not found".format(response["reporter_id"]))
            self.download_user_to_storage(response["reporter_id"], flush)

        result = RhbzBug()
        result.id = response["bug_id"]
        result.summary = response["summary"]
        result.status = response["bug_status"]
        result.creation_time = datetime.datetime.strptime(times["bugs"][0]["creation_time"].value, "%Y%m%dT%H:%M:%S")
        result.last_change_time = datetime.datetime.strptime(times["bugs"][0]["last_change_time"].value, "%Y%m%dT%H:%M:%S")
        if response["bug_status"] == "CLOSED":
            result.resolution = response["resolution"]
            if response["resolution"] == "DUPLICATE":
                if not self.bug_exists_in_storage(response["dupe_id"]):
                    logging.debug("Duplicate #{0} not found".format(response["dupe_id"]))
                    self.download_bug_to_storage(response["dupe_id"], with_comments, with_attachments, flush)
                result.duplicate = response["dupe_id"]
        result.component_id = component.id
        result.opsysrelease_id = opsysrelease.id
        result.creator_id = response["reporter_id"]
        result.whiteboard = response["status_whiteboard"]

        # the bug itself might be downloaded in the duplicate stack
        # exit in this case - it would cause duplicate entry
        if self.bug_exists_in_storage(bug_id):
            logging.debug("Bug #{0} already exists in storage, updating".format(bug_id))
            bugdict = {}
            for col in result.__table__._columns:
                bugdict[col.name] = getattr(result, col.name)

            self.db.session.query(RhbzBug).filter(RhbzBug.id == bug_id).update(bugdict)
        else:
            self.db.session.add(result)

        # important - otherwise we enter endless loop
        if flush:
            self.db.session.flush()

        if "cc" in response:
            logging.debug("Processing CCs")
            userids = self.user_ids_from_logins(response["cc"])
            for userid in userids:
                cc = self.db.session.query(RhbzBugCc).filter((RhbzBugCc.user_id == userid) &
                                                             (RhbzBugCc.bug_id == result.id)).first()
                if cc:
                    logging.debug("CC'ed user #{0} already exists".format(userid))
                    continue

                if not self.user_exists_in_storage(userid):
                    logging.debug("CC'ed user #{0} not found".format(userid))
                    self.download_user_to_storage(userid, flush)

                new = RhbzBugCc()
                new.bug_id = result.id
                new.user_id = userid
                self.db.session.add(new)

        logging.debug("Processing history")
        for event in history:
            userid = self.user_id_from_login(event["who"])
            if not self.user_exists_in_storage(userid):
                logging.debug("History changed by unknown user #{0}".format(userid))
                self.download_user_to_storage(userid, flush)

            for change in event["changes"]:
                chtime = datetime.datetime.strptime(event["when"].value, "%Y%m%dT%H:%M:%S")
                ch = self.db.session.query(RhbzBugHistory).filter((RhbzBugHistory.user_id == userid) &
                                                                  (RhbzBugHistory.time == chtime) &
                                                                  (RhbzBugHistory.field == change["field_name"]) &
                                                                  (RhbzBugHistory.added == change["added"]) &
                                                                  (RhbzBugHistory.removed == change["removed"])).first()
                if ch:
                    logging.debug("Skipping existing history event #{0}".format(ch.id))
                    continue

                new = RhbzBugHistory()
                new.bug_id = bug_id
                new.user_id = userid
                new.time = chtime
                new.field = change["field_name"]
                new.added = change["added"]
                new.removed = change["removed"]

                self.db.session.add(new)

        if with_attachments:
            for attachment in response["attachments"]:
                if self.attachment_exists_in_storage(attachment["attach_id"]):
                    logging.debug("Skipping existing attachment #{0}".format(attachment["attach_id"]))
                    continue

                logging.debug("Downloading attachment #{0}".format(attachment["attach_id"]))
                if not self.user_exists_in_storage(attachment["submitter_id"]):
                    logging.debug("Attachment author #{0} not found".format(attachment["submitter_id"]))
                    self.download_user_to_storage(attachment["submitter_id"], flush)

                new = RhbzAttachment()
                new.id = attachment["attach_id"]
                new.bug_id = result.id
                new.mimetype = attachment["mimetype"]
                new.description = attachment["description"]
                new.filename = attachment["filename"]
                new.is_private = bool(attachment["isprivate"])
                new.is_patch = bool(attachment["ispatch"])
                new.is_obsolete = bool(attachment["isobsolete"])
                new.creation_time = datetime.datetime.strptime(attachment["creation_ts"], "%Y.%m.%d %H:%M")
                new.last_change_time = datetime.datetime.strptime(attachment["modification_time"], "%Y-%m-%d %H:%M:%S")
                new.user_id = attachment["submitter_id"]
                self.db.session.add(new)

                pipe = self.opener.open("{0}?id={1}".format(self.attachment_url, new.id))
                # save_lob is inherited method which cannot be seen by pylint because of sqlalchemy magic
                # pylint: disable=E1101
                new.save_lob("content", pipe, truncate=True, overwrite=True)
                pipe.close()

        if with_comments:
            for comment in response["longdescs"]:
                if self.comment_exists_in_storage(comment["comment_id"]):
                    logging.debug("Skipping existing comment #{0}".format(comment["comment_id"]))
                    continue

                logging.debug("Downloading comment #{0}".format(comment["comment_id"]))
                if not self.user_exists_in_storage(comment["who"]):
                    logging.debug("Comment author #{0} not found".format(comment["who"]))
                    self.download_user_to_storage(comment["who"], flush)

                new = RhbzComment()
                new.id = comment["comment_id"]
                new.bug_id = result.id
                new.creation_time = datetime.datetime.strptime(comment["time"], "%Y-%m-%d %H:%M:%S")
                new.is_private = bool(comment["isprivate"])
                new.comment_type = COMMENT_TYPES[comment["type"]]
                if new.comment_type in ["DUPLICATE_OF", "HAS_DUPLICATE"]:
                    new.duplicate_id = int(comment["extra_data"])
                    if not self.bug_exists_in_storage(new.duplicate_id):
                        logging.debug("Bug #{0} marked as duplicate not found".format(new.duplicate_id))
                        self.download_bug_to_storage(new.duplicate_id, with_comments, with_attachments, flush)
                elif new.comment_type in ["NEW_ATTACHMENT", "COMMENT_ON_ATTACHMENT"]:
                    new.attachment_id = int(comment["extra_data"])
                new.number = comment["count"]
                new.user_id = comment["who"]
                self.db.session.add(new)

                if not isinstance(comment["body"], basestring):
                    comment["body"] = str(comment["body"])

                # save_lob is inherited method which cannot be seen by pylint because of sqlalchemy magic
                # pylint: disable=E1101
                new.save_lob("content", comment["body"].encode("utf-8"), overwrite=True)

        if flush and not self.bug_exists_in_storage(bug_id):
            self.db.session.flush()

        return result

    def attachment_exists_in_storage(self, attachment_id):
        if self.db is None:
            raise Exception, "Storage was not initialized"
        attachment = self.db.session.query(RhbzAttachment).filter(RhbzAttachment.id == attachment_id).first()
        return not attachment is None

    def comment_exists_in_storage(self, comment_id):
        if self.db is None:
            raise Exception, "Storage was not initialized"
        comment = self.db.session.query(RhbzComment).filter(RhbzComment.id == comment_id).first()
        return not comment is None
