from __future__ import absolute_import
from __future__ import unicode_literals

import time
import logging
import datetime

import bugzilla

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

class Bugzilla(object):
    def __init__(self, db, bz_url):
        self.db = db
        self.bz_url = bz_url
        self.bz = bugzilla.Bugzilla(url=bz_url)

        self.add_components = False
        self.add_opsysreleases = False

    def login(self, user, password):
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

    def all_abrt_bugs(self, *args, **kwargs):
        '''
        Fetch all ABRT bugs. Uses the same parameters
        as `all_bugs` function.
        '''

        abrt_specific = dict(
                status_whiteboard='abrt_hash',
                status_whiteboard_type='allwordssubstr',
                product='Fedora',
            )

        kwargs.update(dict(custom_fields=abrt_specific))
        return self.all_bugs(*args, **kwargs)

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

        dbuser = RhbzUser(
            id=user.userid,
            name=user.name,
            email=user.email,
            can_login=user.can_login,
            real_name=user.real_name
            )

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

        logging.info(u'Saving bug #{0}: {1}'.format(bug_dict['bug_id'],
            bug_dict['summary']))

        bug_id = bug_dict['bug_id']

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
            logging.debug('Creator #{0} not found'.format(
                bug_dict['reporter']))

            reporter = self.save_user(self.download_user(bug_dict['reporter']))

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
                    self.save_bug(self.download_bug(bug_dict['dupe_id']))

                new_bug.duplicate = bug_dict['dupe_id']

        new_bug.component_id = component.id
        new_bug.opsysrelease_id = opsysrelease.id
        new_bug.creator_id = reporter.id
        new_bug.whiteboard = bug_dict['status_whiteboard']

        # the bug itself might be downloaded during duplicate processing
        # exit in this case - it would cause duplicate database entry
        if self.get_bug(bug_dict['bug_id']):
            logging.debug('Bug #{0} already exists in storage,'
                'updating'.format(bug_dict['bug_id']))

            bugdict = {}
            for col in new_bug.__table__._columns:
                bugdict[col.name] = getattr(new_bug, col.name)

            (self.db.session.query(RhbzBug)
                .filter(RhbzBug.id == bug_id).update(bugdict))
        else:
            self.db.session.add(new_bug)

        self.db.session.flush()

        self.save_ccs(bug_dict['cc'], new_bug.id)
        self.save_history(bug_dict['history'], new_bug.id)
        self.save_comments(bug_dict['comments'], new_bug.id)
        self.save_attachments(bug_dict['attachments'], new_bug.id)

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

                cced = self.save_user(self.download_user(user_email))

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

                user = self.save_user(self.download_user(user_email))

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
            logging.debug('Processing history event {0}/{1}'.format(num+1,
                total))

            if self.get_attachment(attachment['id']):
                logging.debug('Skipping existing attachment #{0}'.format(
                    attachment['id']))
                continue

            user_email = attachment['attacher']
            user = self.get_user(user_email)

            if not user:
                logging.debug('History changed by unknown user #{0}'.format(
                    user_email))

                user = self.save_user(self.download_user(user_email))

            new = RhbzAttachment()
            new.id = attachment['id']
            new.bug_id = new_bug_id
            new.mimetype = attachment['content_type']
            new.description = attachment['description']
            new.filename = attachment['file_name']
            new.is_private = attachment['is_private']
            new.is_patch = attachment['is_patch']
            new.is_obsolete = attachment['is_obsolete']
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

                user = self.save_user(self.download_user(user_email))

            new = RhbzComment()
            new.id = comment['id']
            new.bug_id = new_bug_id
            new.creation_time = self.convert_datetime(comment['time'])
            new.is_private = comment['is_private']

            if 'attachment_id' in comment:
                new.attachment_id = comment['attachment_id']

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
