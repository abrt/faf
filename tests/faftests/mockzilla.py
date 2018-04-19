import functools
import datetime


class AttrDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Mockzilla(object):
    def __init__(self, *args, **kwargs):
        self.id = 0
        self.first = True
        self.bugs = {}
        now = datetime.datetime.now().replace(microsecond=0)

        self.user = AttrDict(
            userid=42,
            name='User',
            email='u@example.org',
            can_login=True,
            real_name='Example User')

        self.comment = AttrDict(
            id=self.id,
            creator=self.user.email,
            text='test comment',
            time=now,
            is_private=False,
            attachment_id=self.id)

        self.attachment = AttrDict(
            id=self.id,
            attacher=self.user.email,
            content_type='text/plain',
            description='test',
            file_name='fname',
            is_private=False,
            is_patch=False,
            is_obsolete=False,
            creation_time=now,
            last_change_time=now)

        self.history_event = AttrDict(
            who=self.user.email,
            when=now,
            changes=[AttrDict(
                field_name='priority',
                added='High',
                removed='Low')])

        self.last_query_params = {}

    def login(self, *args, **kwargs):
        pass

    def query(self, params_dict):
        self.last_query_params = params_dict

        if self.first:
            self.first = False
            return list(self.bugs.values())
        return []

    def getuser(self, user_email):
        return self.user

    def getbug(self, bug_id,
               include_fields=None, exclude_fields=None, extra_fields=None):
        return self.bugs[bug_id]

    def createbug(self, **data):
        self.id += 1
        now = datetime.datetime.now()
        data['id'] = self.id
        data['bug_id'] = self.id
        data['creation_time'] = now
        data['last_change_time'] = now
        data['status'] = 'NEW'
        data['resolution'] = ''
        data['reporter'] = self.user.email
        data['cc'] = [self.user.email]
        data['comments'] = [self.comment]
        data['attachments'] = [self.attachment]
        history = dict(bugs=[dict(history=[self.history_event])])
        data['get_history_raw'] = lambda: history

        def setwhiteboard(self, bug_id, new, which, comment):
            future = datetime.datetime.now() + datetime.timedelta(days=1)
            self.bugs[bug_id]['{0}_whiteboard'.format(which)] = new
            self.bugs[bug_id]['last_change_time'] = future

            new_comment = AttrDict(
                id=123,
                creator=self.user.email,
                text=comment,
                time=future,
                is_private=False)

            self.bugs[bug_id]['comments'].append(new_comment)

        data['setwhiteboard'] = functools.partial(setwhiteboard, self, self.id)
        self.bugs[self.id] = AttrDict(data)
        return self.bugs[self.id]

    def openattachment(self, attachment_id):
        class mockdata(object):
            def read(self, *args):
                return ''

            def close(self):
                pass

        return mockdata()
