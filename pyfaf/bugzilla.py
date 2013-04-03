from __future__ import absolute_import
from __future__ import unicode_literals

import re
import time
import logging
import datetime

import bugzilla

import pyfaf
from pyfaf import template
from pyfaf.common import retry, daterange

from pyfaf.storage.opsys import (OpSys,
                                 OpSysRelease,
                                 OpSysComponent)

from pyfaf.storage.rhbz import (RhbzBug,
                                RhbzUser,
                                RhbzBugCc,
                                RhbzComment,
                                RhbzAttachment,
                                RhbzBugHistory)

from pyfaf.storage.report import (Report, ReportRhbz, ReportOpSysRelease)
from pyfaf.storage.problem import Problem


class Bugzilla(object):
    def __init__(self, db, bz_url=pyfaf.config.get('bugzilla.url')):
        self.db = db
        self.bz_url = bz_url
        self.bz = None
        if bz_url:
            self.bz = bugzilla.Bugzilla(url=bz_url, cookiefile=None)

        self.add_components = False
        self.add_opsysreleases = False

    def login(self,
              user=pyfaf.config.get('bugzilla.user'),
              password=pyfaf.config.get('bugzilla.password')):
        '''
        Login to bugzilla instance.
        '''
        self.bz.login(user, password)

    def convert_datetime(self, bz_datetime):
        '''
        Convert `bz_datetime` returned by python-bugzilla
        to standard datetime.
        '''

        return datetime.datetime.fromtimestamp(
                    time.mktime(bz_datetime.timetuple()))

    @retry(5, delay=60, backoff=3, verbose=True)
    def query_bugs(self, to_date, from_date,
            limit=100, offset=0, custom_fields=dict()):
        '''
        Perform bugzilla query for bugs since `from_date` to `to_date`.

        Use `custom_fields` to perform additional filtering.
        '''
        logging.info('Fetching bugs modified between '
            '{0} and {1}, offset is: {2}'.format(from_date, to_date, offset))

        que = dict(
                chfieldto=to_date.strftime('%Y-%m-%d'),
                chfieldfrom=from_date.strftime('%Y-%m-%d'),
                query_format='advanced',
                limit=limit,
                offset=offset,
            )

        que.update(custom_fields)

        return self.bz.query(que)

    def all_bugs(self, from_date=datetime.date.today(),
            to_date=datetime.date(2000, 1, 1),
            step=7,
            stop_after_empty_steps=10,
            updated_first=True,
            custom_fields=dict()):
        '''
        Fetch all bugs by creation or modification date
        starting `from_date` until we are not able to find more
        of them or `to_date` is hit.

        Bugs are pulled in date ranges defined by `step`
        not to hit bugzilla timeouts.

        Number of empty queries required before we stop querying is
        controlled by `stop_after_empty_steps`.

        If `updated_first` is True, recently modified bugs
        are queried first.

        `custom_fields` dictionary can be used to create more specific
        bugzilla queries.

        '''

        if not updated_first:
            custom_fields.update(dict(chfield='[Bug creation]'))

        empty = 0

        over_days = list(daterange(from_date, to_date, step, desc=True))
        prev = over_days[0]

        for current in over_days[1:]:
            limit = 100
            offset = 0
            fetched_per_date_range = 0
            while True:
                try:
                    result = self.query_bugs(prev, current,
                                limit, offset, custom_fields)

                except Exception as e:
                    logging.error('Exception after multiple attempts: {0}.'
                        ' Ignoring'.format(e.message))
                    continue

                count = len(result)
                fetched_per_date_range += count
                logging.info('Got {0} bugs'.format(count))
                for bug in result:
                    yield bug

                if not count:
                    logging.debug('No more bugs in this date range')
                    break

                offset += limit

            if not fetched_per_date_range:
                empty += 1
                if empty >= stop_after_empty_steps:
                    break
            else:
                empty = 0

            prev = current - datetime.timedelta(1)

    def all_abrt_bugs(self, product, *args, **kwargs):
        '''
        Fetch all ABRT bugs. Uses the same parameters
        as `all_bugs` function, requires bugzilla `product`
        string.
         '''

        abrt_specific = dict(
                status_whiteboard='abrt_hash',
                status_whiteboard_type='allwordssubstr',
                product=product,
            )

        kwargs.update(dict(custom_fields=abrt_specific))
        return self.all_bugs(*args, **kwargs)

    def update_downloaded_bugs(self):
        """
        Update bugs already present in storage.
        """

        for bug in self.db.session.query(RhbzBug):
            downloaded = self.download_bug(bug.id)
            if downloaded:
                self.save_bug(downloaded)

    def process_bug(self, bug):
        '''
        Process the bug instance and return
        dictionary with fields required by lower logic.

        Returns `None` if there are missing fields.
        '''

        required_fields = [
            'bug_id',
            'creation_time',
            'last_change_time',
            'product',
            'version',
            'component',
            'summary',
            'status',
            'resolution',
            'cc',
            'status_whiteboard',
            'reporter',
            'comments',
            'attachments',
        ]

        bug_dict = dict()
        for field in required_fields:
            if not hasattr(bug, field):
                logging.error('Missing bug field {0}'.format(field))
                return None

            bug_dict[field] = getattr(bug, field)

        for field in ['creation_time', 'last_change_time']:
            bug_dict[field] = self.convert_datetime(bug_dict[field])

        history = bug.get_history()
        bug_dict['history'] = history['bugs'][0]['history']
        if bug.resolution == 'DUPLICATE':
            bug_dict['dupe_id'] = bug.dupe_id

        # handle 'Red Hat Enterprise Linux \d' product naming
        # by stripping the number which is redundant
        if 'Red Hat Enterprise Linux' in bug_dict['product']:
            bug_dict['product'] = ' '.join(bug_dict['product'].split()[:-1])

        return bug_dict

    def get_user(self, user_email):
        '''
        Return RhbzUser instance if there is a user in the database
        with `user_id` id.
        '''

        user = (self.db.session.query(RhbzUser)
                    .filter(RhbzUser.email == user_email).first())
        return user

    @retry(5, delay=60, backoff=3, verbose=True)
    def download_user(self, user_email):
        '''
        Return user with `user_email` downloaded from bugzilla.
        '''

        logging.debug('Downloading user {0}'.format(user_email))
        user = self.bz.getuser(user_email)
        return user

    def save_user(self, user):
        '''
        Save bugzilla `user` to the database. Return persisted
        RhbzUser object.
        '''

        # We need to account for case when user has changed
        # the email address.

        dbuser = (self.db.session.query(RhbzUser)
                    .filter(RhbzUser.id == user.userid).first())

        if not dbuser:
            dbuser = RhbzUser(id=user.userid)

        for field in ['name', 'email', 'can_login', 'real_name']:
            setattr(dbuser, field, getattr(user, field))

        self.db.session.add(dbuser)
        self.db.session.flush()
        return dbuser

    def get_bug(self, bug_id):
        '''
        Return RhbzBug instance if there is a bug in the database
        with `bug_id` id.
        '''

        bug = (self.db.session.query(RhbzBug)
                    .filter(RhbzBug.id == bug_id).first())
        return bug

    @retry(5, delay=60, backoff=3, verbose=True)
    def download_bug(self, bug_id):
        '''
        Return bug with `bug_id` downloaded from bugzilla.
        '''

        logging.debug(u'Downloading bug #{0}'.format(bug_id))
        bug = self.bz.getbug(bug_id)
        return self.process_bug(bug)

    def save_bug(self, bug_dict):
        '''
        Save bug represented by `bug_dict` to the database.

        If bug is marked as duplicate, the duplicate bug is downloaded
        as well.
        '''

        logging.info('Saving bug #{0}: {1}'.format(bug_dict['bug_id'],
            bug_dict['summary']))

        bug_id = bug_dict['bug_id']

        # check if we already have this bug up-to-date
        old_bug = (self.db.session.query(RhbzBug)
            .filter(RhbzBug.id == bug_id)
            .filter(RhbzBug.last_change_time == bug_dict['last_change_time'])
            .first())

        if old_bug:
            logging.info('Bug already up-to-date')
            return old_bug

        opsysrelease = self.get_opsysrelease(bug_dict['product'],
            bug_dict['version'])

        if not opsysrelease:
            logging.error('Unable to save this bug due to unknown release')
            return

        component = self.get_component(opsysrelease, bug_dict['component'])

        if not component:
            logging.error('Unable to save this bug due to unknown component')
            return

        reporter = self.get_user(bug_dict['reporter'])
        if not reporter:
            logging.debug('Creator {0} not found'.format(
                bug_dict['reporter']))

            downloaded = self.download_user(bug_dict['reporter'])
            if not downloaded:
                logging.error('Unable to download user, skipping.')
                return

            reporter = self.save_user(downloaded)

        new_bug = RhbzBug()
        new_bug.id = bug_dict['bug_id']
        new_bug.summary = bug_dict['summary']
        new_bug.status = bug_dict['status']
        new_bug.creation_time = bug_dict['creation_time']
        new_bug.last_change_time = bug_dict['last_change_time']

        if bug_dict['status'] == 'CLOSED':
            new_bug.resolution = bug_dict['resolution']
            if bug_dict['resolution'] == 'DUPLICATE':
                if not self.get_bug(bug_dict['dupe_id']):
                    logging.debug('Duplicate #{0} not found'.format(
                        bug_dict['dupe_id']))

                    downloaded = self.download_bug(bug_dict['dupe_id'])
                    if downloaded:
                        dup = self.save_bug(downloaded)
                        if dup:
                            new_bug.duplicate = dup.id

        new_bug.component_id = component.id
        new_bug.opsysrelease_id = opsysrelease.id
        new_bug.creator_id = reporter.id
        new_bug.whiteboard = bug_dict['status_whiteboard']

        # the bug itself might be downloaded during duplicate processing
        # exit in this case - it would cause duplicate database entry
        if self.get_bug(bug_dict['bug_id']):
            logging.debug('Bug #{0} already exists in storage,'
                ' updating'.format(bug_dict['bug_id']))

            bugdict = {}
            for col in new_bug.__table__._columns:
                bugdict[col.name] = getattr(new_bug, col.name)

            (self.db.session.query(RhbzBug)
                .filter(RhbzBug.id == bug_id).update(bugdict))

            new_bug = self.get_bug(bug_dict['bug_id'])
        else:
            self.db.session.add(new_bug)

        self.db.session.flush()

        self.save_ccs(bug_dict['cc'], new_bug.id)
        self.save_history(bug_dict['history'], new_bug.id)
        self.save_attachments(bug_dict['attachments'], new_bug.id)
        self.save_comments(bug_dict['comments'], new_bug.id)

        return new_bug

    def save_ccs(self, ccs, new_bug_id):
        '''
        Save CC'ed users to the database.

        Expects list of emails (`ccs`) and ID of the bug as `new_bug_id`.
        '''

        total = len(ccs)
        for num, user_email in enumerate(ccs):
            logging.debug('Processing CC: {0}/{1}'.format(num+1, total))
            cc = (self.db.session.query(RhbzBugCc)
                .join(RhbzUser)
                .filter((RhbzUser.email == user_email) &
                        (RhbzBugCc.bug_id == new_bug_id)).first())

            if cc:
                logging.debug('CC\'ed user {0} already'
                    ' exists'.format(user_email))
                continue

            cced = self.get_user(user_email)
            if not cced:
                logging.debug('CC\'ed user {0} not found,'
                    ' adding.'.format(user_email))

                downloaded = self.download_user(user_email)
                if not downloaded:
                    logging.error('Unable to download user, skipping.')
                    continue

                cced = self.save_user(downloaded)

            new = RhbzBugCc()
            new.bug_id = new_bug_id
            new.user = cced
            self.db.session.add(new)

        self.db.session.flush()

    def save_history(self, events, new_bug_id):
        '''
        Save bug history to the database.

        Expects list of `events` and ID of the bug as `new_bug_id`.
        '''

        total = len(events)
        for num, event in enumerate(events):
            logging.debug('Processing history event {0}/{1}'.format(num+1,
                total))

            user_email = event['who']
            user = self.get_user(user_email)

            if not user:
                logging.debug('History changed by unknown user #{0}'.format(
                    user_email))


                downloaded = self.download_user(user_email)
                if not downloaded:
                    logging.error('Unable to download user, skipping.')
                    continue

                user = self.save_user(downloaded)

            for change in event['changes']:
                chtime = self.convert_datetime(event['when'])
                ch = (self.db.session.query(RhbzBugHistory)
                        .filter((RhbzBugHistory.user == user) &
                                (RhbzBugHistory.time == chtime) &
                                (RhbzBugHistory.field == change['field_name']) &
                                (RhbzBugHistory.added == change['added']) &
                                (RhbzBugHistory.removed == change['removed']))
                        .first())
                if ch:
                    logging.debug('Skipping existing history event '
                        '#{0}'.format(ch.id))
                    continue

                new = RhbzBugHistory()
                new.bug_id = new_bug_id
                new.user = user
                new.time = chtime
                new.field = change['field_name']
                new.added = change['added']
                new.removed = change['removed']

                self.db.session.add(new)

        self.db.session.flush()

    def get_attachment(self, attachment_id):
        '''
        Return RhbzAttachment instance if there is an attachment in
        the database with `attachment_id` id.
        '''

        attachment = (self.db.session.query(RhbzAttachment)
            .filter(RhbzAttachment.id == attachment_id).first())
        return attachment

    def save_attachments(self, attachments, new_bug_id):
        '''
        Save bug attachments to the database.

        Expects list of `attachments` and ID of the bug as `new_bug_id`.
        '''

        total = len(attachments)
        for num, attachment in enumerate(attachments):
            logging.debug('Processing attachment {0}/{1}'.format(num+1,
                total))

            if self.get_attachment(attachment['id']):
                logging.debug('Skipping existing attachment #{0}'.format(
                    attachment['id']))
                continue

            user_email = attachment['attacher']
            user = self.get_user(user_email)

            if not user:
                logging.debug('Attachment from unknown user {0}'.format(
                    user_email))

                downloaded = self.download_user(user_email)
                if not downloaded:
                    logging.error('Unable to download user, skipping.')
                    continue

                user = self.save_user(downloaded)

            new = RhbzAttachment()
            new.id = attachment['id']
            new.bug_id = new_bug_id
            new.mimetype = attachment['content_type']
            new.description = attachment['description']
            new.filename = attachment['file_name']
            new.is_private = bool(attachment['is_private'])
            new.is_patch = bool(attachment['is_patch'])
            new.is_obsolete = bool(attachment['is_obsolete'])
            new.creation_time = self.convert_datetime(
                attachment['creation_time'])
            new.last_change_time = self.convert_datetime(
                attachment['last_change_time'])
            new.user = user
            self.db.session.add(new)

            data = self.bz.openattachment(attachment['id'])
            # save_lob is inherited method which cannot be seen by pylint
            # because of sqlalchemy magic
            # pylint: disable=E1101
            new.save_lob('content', data, truncate=True, overwrite=True)
            data.close()

        self.db.session.flush()

    def get_comment(self, comment_id):
        '''
        Return RhbzComment instance if there is a comment in the database
        with `comment_id` id.
        '''

        comment = (self.db.session.query(RhbzComment)
            .filter(RhbzComment.id == comment_id).first())
        return comment

    def save_comments(self, comments, new_bug_id):
        '''
        Save bug comments to the database.

        Expects list of `comments` and ID of the bug as `new_bug_id`.
        '''

        total = len(comments)
        for num, comment in enumerate(comments):
            logging.debug('Processing comment {0}/{1}'.format(num+1,
                total))

            if self.get_comment(comment['id']):
                logging.debug('Skipping existing comment #{0}'.format(
                    comment['id']))
                continue

            logging.debug('Downloading comment #{0}'.format(comment['id']))

            user_email = comment['creator']
            user = self.get_user(user_email)

            if not user:
                logging.debug('History changed by unknown user #{0}'.format(
                    user_email))

                downloaded = self.download_user(user_email)
                if not downloaded:
                    logging.error('Unable to download user, skipping.')
                    continue

                user = self.save_user(downloaded)

            new = RhbzComment()
            new.id = comment['id']
            new.bug_id = new_bug_id
            new.creation_time = self.convert_datetime(comment['time'])
            new.is_private = comment['is_private']

            if 'attachment_id' in comment:
                attachment = self.get_attachment(comment['attachment_id'])
                if attachment:
                    new.attachment = attachment
                else:
                    logging.warning('Comment is referencing an attachment'
                        ' which is not accessible.')

            new.number = num
            new.user = user
            self.db.session.add(new)

            if not isinstance(comment['text'], basestring):
                comment['text'] = str(comment['text'])

            # save_lob is inherited method which cannot
            # be seen by pylint because of sqlalchemy magic
            # pylint: disable=E1101
            new.save_lob('content', comment['text'].encode('utf-8'),
                overwrite=True)

        self.db.session.flush()

    def get_opsysrelease(self, product, version):
        '''
        Return OpSysRelease instance matching `product`
        and `version` parameters.

        Optionally creates new OpSys and OpSysRelease
        if `self.add_opsysreleases` is enabled.
        '''

        opsysrelease = (
            self.db.session.query(OpSysRelease)
              .join(OpSys)
              .filter((OpSys.name == product) &
                      (OpSysRelease.version == version))
              .first())

        if not opsysrelease:
            if not self.add_opsysreleases:
                logging.error('Unable to find release "{0} {1}"'.format(
                    product, version))

                return None
            else:
                logging.error('Unable to find release "{0} {1}". '
                ' Adding new one.'.format(
                    product, version))

                opsys = (self.db.session.query(OpSys)
                            .filter(OpSys.name == product)
                            .first())

                if not opsys:
                    opsys = OpSys(name = product)
                    self.db.session.add(opsys)

                opsysrelease = OpSysRelease(opsys = opsys, status="ADDED",
                    version = version)
                self.db.session.add(opsysrelease)
                self.db.session.flush()

        return opsysrelease

    def get_component(self, opsysrelease, component_name):
        '''
        Return OpSysComponent instance matching `component_name`
        which also belongs to OpSysRelase instance passed as `opsysrelease`.

        Optionally creates new OpSysComponent
        if `self.add_opsyscomponents` is enabled.
        '''

        component = (
            self.db.session.query(OpSysComponent)
               .join(OpSys)
               .filter((OpSys.id == opsysrelease.opsys.id) &
                       (OpSysComponent.name == component_name))
               .first())

        if not component:
            if not self.add_components:
                logging.error('Unable to find component "{0}" in "{1}"'.format(
                    component_name, opsysrelease.opsys.name))

                return None
            else:
                logging.info('Unable to find component "{0}" in "{1}"'
                    '. Adding new one.'.format(component_name,
                        opsysrelease.opsys.name))

                component = OpSysComponent(name = component_name,
                    opsys = opsysrelease.opsys)

                self.db.session.add(component)
                self.db.session.flush()

        return component

    @retry(5, delay=60, backoff=3, verbose=True)
    def set_whiteboard(self, bug_id, new_whiteboard, comment=None):
        bug = self.bz.getbug(bug_id)
        bug.setwhiteboard(new_whiteboard, 'status', comment)

    @retry(5, delay=60, backoff=3, verbose=True)
    def create_bug(self, **data):
        return self.bz.createbug(**data)

    def create_bugs(self, problem_list,
                    summary_template='bugzilla_new_summary',
                    description_template='bugzilla_new_body',
                    dry_run=False):
        '''
        Iterate over `problem_list` and create bugzilla tickets
        for these problems.

        After the ticket creation, it downloads the bug and assigns
        it to respective problem.
        '''

        total = len(problem_list)
        for num, problem in enumerate(problem_list):
            logging.info('Processing problem #{0}, {1} of {2}'.format(
                problem.id, num + 1, total))

            data = dict(problem=problem)
            components = problem.unique_component_names

            if not components:
                logging.error('Problem has no components, skipping.')
                continue

            if len(components) > 1:
                data['all_components'] = ' '.join(components)

            # pick first and assign this bug to it
            data['component'] = components.pop()

            if not problem.reports:
                logging.warning('Refusing to process problem with no reports.')
                continue

            report = problem.sorted_reports[0]
            if not report.backtraces:
                logging.warning('Refusing to process report with no backtrace.')
                continue

            if pyfaf.kb.report_in_kb(self.db, report):
                logging.info('Report matches knowledge base entry, skipping.')
                continue

            if report.packages:
                data['package'] = report.packages[0].installed_package
            if report.reasons:
                data['reason'] = report.reasons[0]

            data['type'] = report.type
            data['first_occurence'] = problem.first_occurence
            data['reports_count'] = problem.reports_count

            if report.executables:
                data['executable'] = report.executables[0].path

            data['duphash'] = report.backtraces[0].hash
            data['faf_hash'] = report.backtraces[0].hash

            highest_version = -1
            highest_release = None

            for report_release in report.opsysreleases:
                if report_release.opsysrelease.version > highest_version:
                    highest_version = report_release.opsysrelease.version
                    highest_release = report_release.opsysrelease

            if not highest_release:
                logging.error('No OpSysRelease assigned to this report,'
                              ' skipping')
                continue

            data['os_release'] = highest_release
            if report.arches:
                data['architecture'] = report.arches[0]

            # format backtrace
            backtrace_headers = {
                'USERSPACE': ['#', 'Function', 'Path', 'Source'],
                'KERNELOOPS': ['#', 'Function', 'Binary', 'Source'],
                'PYTHON': ['#', 'Function', 'Source'],
            }
            if not report.type in backtrace_headers:
                logging.error('Do not know how to format backtrace for report'
                              ' type {0}, skipping.'.format(report.type))

                continue

            backtrace_header = backtrace_headers[report.type]

            frames = report.backtraces[0].as_named_tuples()
            our_frames = []
            for position, frame in enumerate(frames):
                more = ''
                name = frame.name

                # strip arguments in case of c++ function names containing
                # long lists of them
                if '(' in name:
                    name = name.split('(')[0]

                if frame.source_path and frame.line_num:
                    more = '{0}:{1}'.format(frame.source_path, frame.line_num)

                if report.type == 'PYTHON':
                    our_frames.append((position, name,
                                      '{0}:{1}'.format(frame.source_path,
                                                       frame.line_num)))
                else:
                    our_frames.append((position, name, frame.path, more))

            data['backtrace'] = pyfaf.support.as_table(
                backtrace_header, our_frames,
                margin=2)

            summary = template.render(summary_template, data)
            description = template.render(description_template, data)

            bz_data = dict()
            bz_data['component'] = str(data['component'])
            bz_data['product'] = str(data['os_release'].opsys)
            bz_data['version'] = str(data['os_release'].version)
            bz_data['summary'] = summary
            bz_data['description'] = description
            bz_data['status_whiteboard'] = 'abrt_hash:{0} reports:{1}'.format(
                data['duphash'], data['reports_count'])

            if dry_run:
                print(summary)
                print(description)
                logging.info('Dry run enabled. Not performing any action.')
                continue

            try:  # create
                new_bug = self.create_bug(**bz_data)
            except:
                logging.error('Unable to create new bug')
                continue

            bug = None
            try:  # download
                downloaded = self.download_bug(new_bug.id)
                if downloaded:
                    bug = self.save_bug(downloaded)
            except:
                raise
                logging.error('Unable to download bug #{0}'.format(new_bug.id))
                continue

            # connect to report
            if bug:
                new = ReportRhbz()
                new.report = report
                new.rhbzbug = bug
                self.db.session.add(new)
                self.db.session.flush()

    def update_bugs(self, problem_list,
                    template_name='bugzilla_update_comment',
                    dry_run=False):
        '''
        Iterate over `problem_list` and add comment to bugs
        that has no comment from us or where our comment
        is outdated (report count is less than half of current
        report count).
        '''
        reports_count_regex = re.compile('reports:(\d+)')

        total = len(problem_list)
        for num, problem in enumerate(problem_list):
            logging.info('Processing problem #{0}, {1} of {2}'.format(
                problem.id, num + 1, total))

            current_count = problem.reports_count

            buglist = problem.bugs
            btotal = len(buglist)

            for bnum, bug in enumerate(problem.bugs):
                logging.debug('Checking bug #{0}, {1} of {2}'.format(
                    bug.id, bnum + 1, btotal))

                new_wb = None

                if 'reports:' in bug.whiteboard:
                    matches = reports_count_regex.finditer(bug.whiteboard)
                    res = list(matches)[0]
                    if res:
                        previous_count = int(res.group(1))
                        logging.debug('Previous report count: {0}'.format(
                            previous_count))
                        logging.debug('Current report count: {0}'.format(
                            current_count))
                        # previous number of reports should never be smaller
                        # than current number of reports
                        assert(previous_count <= current_count)

                        # if there's our comment we only add new one
                        # when number of reports is twice as high
                        if previous_count * 2 >= current_count:
                            logging.info('Current number of reports is'
                                         ' not high enough. Not updating')
                            continue

                        replacement = 'reports:{0}'.format(current_count)
                        new_wb = reports_count_regex.sub(replacement,
                                                         bug.whiteboard,
                                                         count=1)

                if not new_wb:
                    if not bug.whiteboard:
                        new_wb = 'reports:{0}'.format(current_count)
                    else:
                        new_wb = '{0} reports:{1}'.format(bug.whiteboard,
                                                          current_count)

                # get top report
                if not problem.reports:
                    logging.warning('Refusing to process problem with no reports.')
                    continue

                report = problem.sorted_reports[0]
                if not report.backtraces:
                    logging.warning('Refusing to process report with no backtrace.')
                    continue

                faf_hash = report.backtraces[0].hash

                comment = template.render(template_name,
                                          dict(report_count=current_count,
                                               problem=problem,
                                               faf_hash=faf_hash))

                logging.info('Adding comment to bug #{0}.'
                             ' Comment:\n\n{1}\n'.format(bug.id, comment))

                if dry_run:
                    logging.info('Dry run enabled. Not performing any action.')
                    continue

                try:
                    self.set_whiteboard(bug.id, new_wb, comment)
                    downloaded = self.download_bug(bug.id)
                    if downloaded:
                        bug = self.save_bug(downloaded)
                except KeyboardInterrupt:
                    return
                except:
                    logging.error('Unable to add update bug #{0}'.format(bug.id))


def query_no_ticket(db, opsys_name, opsys_version=None,
                    minimal_reports_threshold=10):
    '''
    Return list of problems without bugzilla tickets with
    report count over `minimal_reports_threshold`.

    Problems can be queried for specific `opsys_name`
    and `opsys_version`.
    '''

    opsysquery = (
        db.session.query(OpSysRelease.id)
        .join(OpSys)
        .filter(OpSys.name == opsys_name))

    if opsys_version:
        opsysquery = opsysquery.filter(OpSys.version == opsys_version)

    opsysrelease_ids = [row[0] for row in opsysquery.all()]

    probs = (
        db.session.query(Problem)
        .join(Report)
        .join(ReportOpSysRelease)
        .filter(Report.count >= minimal_reports_threshold)
        .filter(~Report.id.in_(
            db.session.query(ReportRhbz.report_id).subquery()
        ))
        .filter(ReportOpSysRelease.opsysrelease_id.in_(opsysrelease_ids))
        .distinct(Problem.id)).all()

    return probs


def query_update_candidates(db, opsys_name, opsys_version=None,
                            minimal_reports_threshold=50):
    '''
    Return list of problems with bugzilla tickets
    which are not CLOSED and have more reports
    than `minimal_reports_threshold`.

    Problems can be queried for specific `opsys_name`
    and `opsys_version`.
    '''

    opsysquery = (
        db.session.query(OpSysRelease.id)
        .join(OpSys)
        .filter(OpSys.name == opsys_name))

    if opsys_version:
        opsysquery = opsysquery.filter(OpSys.version == opsys_version)

    opsysrelease_ids = [row[0] for row in opsysquery.all()]

    probs = (
        db.session.query(Problem)
        .join(Report)
        .join(ReportOpSysRelease)
        .filter(Report.count >= minimal_reports_threshold)
        .filter(Report.id.in_(
            db.session.query(ReportRhbz.report_id)
            .join(RhbzBug)
            .filter(RhbzBug.status != 'CLOSED')
            .subquery()))
        .filter(ReportOpSysRelease.opsysrelease_id.in_(
            opsysrelease_ids))
        .distinct(Problem.id)).all()

    return probs
