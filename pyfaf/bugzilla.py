import xmlrpclib
import pprint
import cookielib
import logging
import urllib2
import sys
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

pretty_printer = pprint.PrettyPrinter(indent=2)

COMMENT_TYPES = ["NORMAL", "DUPLICATE_OF", "HAS_DUPLICATE", "POPULAR_VOTES", "MOVED_TO", "NEW_ATTACHMENT", "COMMENT_ON_ATTACHMENT"]

class CookieResponse:
    """
    Fake HTTPResponse object that we can fill with headers we got
    elsewhere.  We can then pass it to CookieJar.extract_cookies() to
    make it pull out the cookies from the set of headers we have.
    Taken from python-bugzilla.
    """
    def __init__(self, headers):
        self.headers = headers
    def info(self):
        return self.headers

class SafeCookieTransport(xmlrpclib.SafeTransport):
    """
    SafeTransport subclass that supports cookies.
    Taken from python-bugzilla.
    """
    scheme = 'https'
    cookiejar = None

    def send_cookies(self, connection, cookie_request):
        if self.cookiejar is None:
            self.cookiejar = cookielib.CookieJar()
        elif self.cookiejar:
            self.cookiejar.add_cookie_header(cookie_request)
            # Pull the cookie headers out of the request object...
            cookielist = list()
            for header, value in cookie_request.header_items():
                if header.startswith('Cookie'):
                    cookielist.append([header, value])
            # ...and put them over the connection
            for header, value in cookielist:
                connection.putheader(header, value)

    # python <= 2.6 does not use single_request
    def request(self, host, handler, request_body, verbose=0):
        return self.single_request(host, handler, request_body, verbose)

    def single_request(self, host, handler, request_body, verbose=0):
        connection = self.make_connection(host)
        request_url = "{0}://{1}{2}".format(self.scheme, host, handler)
        cookie_request  = urllib2.Request(request_url)

        # Try it several times because Bugzilla likes to respond with
        # 502 Proxy Error without any reason.
        for attempt in range(0, 5):
            try:
                self.send_request(connection, handler, request_body)
                self.send_host(connection, host)
                self.send_cookies(connection, cookie_request)
                self.send_user_agent(connection)
                self.send_content(connection, request_body)
                # python <= 2.6 does not provide .getresponse()
                if sys.version_info[0] <= 2 and sys.version_info[1] <= 6:
                    errcode, errmsg, headers = connection.getreply()
                    response = connection.getfile()
                    cookie_response = CookieResponse(headers)
                    self.cookiejar.extract_cookies(cookie_response, cookie_request)
                    if errcode != 200:
                        continue

                    self.verbose = verbose
                    return self.parse_response(response)
                else:
                    response = connection.getresponse(buffering=True)
                    cookie_response = CookieResponse(response.msg)
                    self.cookiejar.extract_cookies(cookie_response, cookie_request)
                    if response.status != 200:
                        continue

                    self.verbose = verbose
                    return self.parse_response(response)


            except xmlrpclib.Fault:
                raise

        if sys.version_info[0] <= 2 and sys.version_info[1] <= 6:
            raise xmlrpclib.ProtocolError(host + handler, errcode,
                                          errmsg, headers)
        else:
            if response.getheader("content-length", 0):
                response.read()
            raise xmlrpclib.ProtocolError(host + handler, response.status,
                                          response.reason, response.msg)

class Bugzilla:
    def __init__(self, url, db=None):
        self.url = url
        self.transport = SafeCookieTransport()
        self.proxy = xmlrpclib.ServerProxy(self.url, self.transport)
        self.attachment_url = self.url.replace('xmlrpc.cgi','attachment.cgi')
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.transport.cookiejar))
        self.db = db

        self.cache_user_login_to_id = {}
        self.comment_bug_cache = {}
        self.comment_author_cache = {}

    def login(self, user, password):
        self.proxy.User.login({"login":user, "password":password})

    def user_ids_from_logins(self, logins):
        # Build array of logins we need to fetch from Bugzilla.
        # Some logins are cached.
        requested_logins = []
        for login in logins:
            if login not in self.cache_user_login_to_id:
                requested_logins.append(login)

        if len(requested_logins) > 0:
            response = self.proxy.User.get({"names":requested_logins,
                                            "include_fields":["id", "name"]})
            for response_user in response["users"]:
                self.cache_user_login_to_id[response_user["name"]] = int(response_user["id"])
        return [self.cache_user_login_to_id[login] for login in logins]

    def user_id_from_login(self, login):
        return self.user_ids_from_logins([login])[0]

    def new_bug(self,
                raw,
                product,
                version,
                component,
                summary,
                description,
                depends_on=None,
                blocks=None):
        bug = {"product" : product,
               "version" : version,
               "component" : component,
               "short_desc" : summary,
               "comment" : description}
        if depends_on is not None:
            bug["dependson"] = depends_on
        if blocks is not None:
            bug["blocked"] = blocks
        response = self.proxy.Bug.create(bug)
        if raw:
            pretty_printer.pprint(response)
        return response["id"]

    def bug_fields(self):
        """
        Prints available bug fields to stdout.
        """
        response = self.proxy.Bug.fields()
        response_fields = response["fields"]
        for i in range(0, len(response_fields)):
            if "values" in response_fields[i]:
                del response_fields[i]["values"]
        pretty_printer.pprint(response_fields)

    def search_bugs(self,
                    raw,
                    whiteboard,
                    whiteboard_type,
                    order,
                    chfield_from,
                    chfield_to,
                    chfield,
                    product,
                    product_version,
                    output_format,
                    return_list=False):
        # Bug.search is full of bugs -> useless for our purposes
        # "limit":"10"
        query = {'column_list':[]}
        if output_format is None:
            output_format = "%{bug_id}"
        else:
            if "%{product}" in output_format:
                query['column_list'].append("product")
            if "%{last_changed_time}" in output_format:
                query['column_list'].append("changeddate")
        query['column_list'] = ",".join(query['column_list'])
        if whiteboard is not None:
            query['status_whiteboard'] = whiteboard
        if whiteboard_type is not None:
            query['status_whiteboard_type'] = whiteboard_type
        if order is not None:
            query['order'] = order
        if chfield_from is not None:
            query['chfieldfrom'] = chfield_from
        if chfield_to is not None:
            query['chfieldto'] = chfield_to
        if chfield is not None:
            query['chfield'] = chfield
        if product is not None:
            query['product'] = product
        if product_version is not None:
            query['version'] = product_version
        #{'status_whiteboard_type':'allwordssubstr',
        # 'status_whiteboard':'abrt_hash',
        # "order":"Last Changed",
        # "column_list":[]}
        response = self.proxy.bugzilla.runQuery(query)
        if return_list:
            return response["bugs"]

        if raw:
            pretty_printer.pprint(response)
        sys.stdout.write("< search\n")
        bug_ids = map(lambda x: x["bug_id"], response["bugs"])
        for bug in reversed(response["bugs"]):
            output = output_format.replace("%{bug_id}", str(bug["bug_id"]))
            if "product" in bug:
                output = output.replace("%{product}", bug["product"][0])
            if "changeddate" in bug:
                time = datetime.datetime.strptime(bug["changeddate"], "%Y-%m-%d %H:%M:%S")
                output = output.replace("%{last_changed_time}", time.strftime("%Y-%m-%dT%H:%M:%S.%f%z"))
            sys.stdout.write("{0}\n".format(output))
        sys.stdout.write("< ok\n")

    def close_as_duplicate(self, close_id, dupe_id, comment=None):
        query = {"ids": [close_id], "updates": {"dupe_id": dupe_id}}
        if comment:
            query["updates"]["comment"] = comment
        self.proxy.Bug.update(query)

    def add_comment(self, bug_id, comment):
        response = self.proxy.Bug.add_comment({"id": bug_id, "comment": comment})
        return response["id"]

    def change_component(self, bug_id, component_name, comment=None):
        query = {"ids": [bug_id], "updates": {"component": component_name, "set_default_assignee": True, "set_default_qa_contact": True}}
        if comment:
            query["updates"]["comment"] = comment
        self.proxy.Bug.update(query)

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
