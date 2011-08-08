# Copyright (C) 2011 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import re
import sys
import datetime
import base64
import binascii

class TemplateItem:
    def __init__(self, variable_name, text_name, database_is_stored, database_has_separate_table, database_indexed):
        self.variable_name = variable_name
        self.text_name = text_name
        self.database_is_stored = database_is_stored
        self.database_has_separate_table = database_has_separate_table
        self.database_indexed = database_indexed
        if self.text_name is None:
            self.text_name = re.sub('_', '', variable_name.title())
        self.parse_line_start_lower = u"{0}:".format(self.text_name.lower())
        self.parent = None

    def to_text(self, instance):
        sys.stderr.write(u"Unimplemented method to_text.\n")
        exit(1)

    def focus_can_parse_line(self, line):
        sys.stderr.write(u"Unimplemented method focus_can_parse_line.\n")
        exit(1)

    def focus_parse_line(self, line, instance):
        sys.stderr.write(u"Unimplemented method focus_parse_line.\n")
        exit(1)

    def focus_terminate(self, instance):
        sys.stderr.write(u"Unimplemented method focus_terminate.\n")
        exit(1)

    def can_parse_line(self, line):
        sys.stderr.write(u"Unimplemented method can_parse_line.\n")
        exit(1)

    def parse_line(self, line, instance):
        sys.stderr.write(u"Unimplemented method parse_line.\n")
        exit(1)

    def is_valid(self, instance):
        sys.stderr.write(u"Unimplemented method is_valid.\n")
        exit(1)

    def value(self, instance):
        return getattr(instance, self.variable_name)

    def to_database(self, instance, cursor, table_prefix):
        sys.stderr.write(u"Unimplemented method to_database.\n")
        exit(1)

    def database_create_table(self, cursor, table_prefix):
        sys.stderr.write(u"Unimplemented method database_create_table.\n")
        exit(1)

class TopLevelItem(TemplateItem):
    def __init__(self, name, klass, klass_template):
        TemplateItem.__init__(self, name, None,
                              database_is_stored=True,
                              database_has_separate_table=True,
                              database_indexed=False)
        self.klass = klass
        self.klass_template = klass_template
        for item in self.klass_template:
            item.parent = self

    def database_table_name(self, table_prefix):
        if table_prefix:
            return u"{0}_{1}".format(table_prefix, self.variable_name)
        else:
            return self.variable_name

    def to_database(self, instance, cursor, table_prefix=u""):
        stored_items = [item for item in self.klass_template if item.database_is_stored]
        this_table_items = [item for item in stored_items if not item.database_has_separate_table]
        other_table_items = [item for item in stored_items if item.database_has_separate_table]
        cursor.execute(u"insert into {0} values ({1})".format(self.database_table_name(table_prefix),
                                                              u", ".join([u"?" for item in this_table_items])),
                       [item.value(instance) for item in this_table_items])
        [item.to_database(instance, cursor, table_prefix) for item in other_table_items]

    def database_create_table(self, cursor, table_prefix=u""):
        stored_items = [item for item in self.klass_template if item.database_is_stored]
        this_table_items = [item for item in stored_items if not item.database_has_separate_table]
        other_table_items = [item for item in stored_items if item.database_has_separate_table]
        cursor.execute(u"create table if not exists {0} ({1})".format(self.database_table_name(table_prefix),
                                                                      u", ".join([item.variable_name for item in this_table_items])))
        for item in this_table_items:
            if item.database_indexed:
                cursor.execute(u"create index if not exists {0}_{1} on {0} ({1})".format(self.database_table_name(table_prefix),
                                                                                         item.variable_name))
        [item.database_create_table(cursor, table_prefix) for item in other_table_items]

    def to_text(self, instance):
        return u"".join([item.to_text(instance) for item in self.klass_template])

    def from_text(self, text):
        instance = self.klass()
        self.update_from_text(instance, text)
        return instance

    def update_from_text(self, instance, text):
        focused_template = None
        for line in text.splitlines():
            if focused_template:
                if focused_template.focus_can_parse_line(line):
                    focused_template.focus_parse_line(line, instance)
                    continue
                else:
                    focused_template.focus_terminate(instance)
                    focused_template = None
            found = False
            for item in self.klass_template:
                if item.can_parse_line(line):
                    obtain_focus = item.parse_line(line, instance)
                    if obtain_focus:
                        focused_template = item
                    found = True
                    break
            if not found:
                sys.stderr.write(u"Unknown input: {0}.\n".format(line))
                exit(1)
        if focused_template:
            focused_template.focus_terminate(instance)

    def is_valid(self, instance):
        if not isinstance(instance, self.klass):
            return u"Expected {0} type, but found {2}.".format(self.klass.__name__,  instance.__class__.__name__)
        for item in self.klass_template:
            valid = item.is_valid(instance)
            if valid != True:
                return valid
        return True

class TemplateItemString(TemplateItem):
    def __init__(self, variable_name, text_name, multiline, null, constraint, database_indexed):
        TemplateItem.__init__(self, variable_name, text_name,
                              database_is_stored=True, database_has_separate_table=False,
                              database_indexed=database_indexed)
        self.multiline = multiline
        self.null = null
        self.constraint = constraint

    def to_text(self, instance):
        # Convert only valid values into text.
        valid = self.is_valid(instance)
        if valid != True:
            sys.stderr.write(u"{0}\n".format(valid))
            exit(1)
        value = self.value(instance)
        if value is None:
            return u""
        if self.multiline:
            result = [u"{0}:\n".format(self.text_name)]
            result.extend([u"  {0}\n".format(line) for line in value.splitlines()])
            return u"".join(result)
        else:
            return u"{0}: {1}\n".format(self.text_name, value)

    def focus_can_parse_line(self, line):
        return line.startswith(u"  ")

    def focus_parse_line(self, line, instance):
        self.focus_cache.append(line[2:])

    def focus_terminate(self, instance):
        setattr(instance, self.variable_name, u"\n".join(self.focus_cache))
        self.focus_cache = [] # Don't keep long text in memory

    def can_parse_line(self, line):
        return line.lower().startswith(self.parse_line_start_lower)

    def parse_line(self, line, instance):
        if self.multiline:
            self.focus_cache = []
            # Read the rest of the initial line and if nonempty,
            # consider it as the first line. This way, multiline
            # string entry can still read single-line entries, which
            # is good for managing changes.
            rest_of_line = line[len(self.parse_line_start_lower):].strip()
            if len(rest_of_line) > 0:
                self.focus_cache.append(rest_of_line)
            return True
        setattr(instance, self.variable_name, line[len(self.parse_line_start_lower):].strip())
        return False

    def is_valid(self, instance):
        value = self.value(instance)
        can_be_null = self.null
        if hasattr(can_be_null, u"__call__"):
            can_be_null = can_be_null(instance)
        if (value is None or len(value) == 0) and not can_be_null:
            return u"Missing value of '{0}' in {1}.".format(self.variable_name, instance.__class__.__name__)
        if value is not None:
            if not isinstance(value, basestring):
                return u"Expected str type of '{0}' in {1}.".format(self.variable_name, instance.__class__.__name__)
            if self.constraint is not None and not self.constraint(value, instance):
                return u"Failed to validate the value of '{0}' in {1} by external validator.".format(self.variable_name,
                                                                                                    instance.__class__.__name__)
        return True

class TemplateItemArray(TemplateItem):
    def __init__(self, variable_name, text_name, type_, database_indexed):
        TemplateItem.__init__(self, variable_name, text_name,
                              database_is_stored=True, database_has_separate_table=True,
                              database_indexed=database_indexed)
        self.type = type_

    def to_text(self, instance):
        # Convert only valid values into text.
        valid = self.is_valid(instance)
        if valid != True:
            sys.stderr.write(u"{0}\n".format(valid))
            exit(1)
        value = self.value(instance)
        if len(value) == 0:
            return u""
        return u"{0}:\n- {1}\n".format(self.text_name,
                                       u"\n- ".join([unicode(item) for item in value]))

    def focus_can_parse_line(self, line):
        return line.startswith(u"- ")

    def focus_parse_line(self, line, instance):
        self.focus_cache.append(self.type(line[2:]))

    def focus_terminate(self, instance):
        setattr(instance, self.variable_name, self.focus_cache)
        self.focus_cache = [] # Don't keep long list in memory

    def can_parse_line(self, line):
        return line.lower().startswith(self.parse_line_start_lower)

    def parse_line(self, line, instance):
        self.focus_cache = []
        return True

    def is_valid(self, instance):
        value = self.value(instance)
        if not isinstance(value, list):
            return u"Expected list type of '{0}'.".format(self.variable_name)
        for item in value:
            if not isinstance(item, self.type):
                return u"Expected {0} type of item in '{1}', but found {2}.".format(self.type.__name__,
                                                                                    self.variable_name,
                                                                                    item.__class__.__name__)
        return True

    def database_table_name(self, table_prefix):
        return u"{0}_{1}".format(self.parent.database_table_name(table_prefix),
                                self.variable_name)

    def to_database(self, instance, cursor, table_prefix):
        value = self.value(instance)
        for item in value:
            cursor.execute(u"insert into {0} values (?, ?)".format(self.database_table_name(table_prefix)),
                           (instance.id, item))

    def database_create_table(self, cursor, table_prefix):
        cursor.execute(u"create table if not exists {0} ({1}_id, value)".format(self.database_table_name(table_prefix),
                                                                                self.parent.variable_name))
        if self.database_indexed:
            cursor.execute(u"create index if not exists {0}_{1}_id on {0} ({1}_id)".format(self.database_table_name(table_prefix),
                                                                                           self.parent.variable_name))
            cursor.execute(u"create index if not exists {0}_value on {0} (value)".format(self.database_table_name(table_prefix)))

class TemplateItemArrayDict(TemplateItem):
    def __init__(self, variable_name, text_name, klass, klass_template, database_indexed):
        TemplateItem.__init__(self, variable_name, text_name,
                              database_is_stored=True, database_has_separate_table=True,
                              database_indexed=database_indexed)
        self.klass = klass # dict class
        self.klass_template = klass_template # template for the dict class
        for item in self.klass_template:
            item.parent = self

    def to_text(self, instance):
        # Convert only valid values into text.
        valid = self.is_valid(instance)
        if valid != True:
            sys.stderr.write(u"{0}\n".format(valid))
            exit(1)
        value = self.value(instance)
        if len(value) == 0:
            return u""
        result = [u"{0}:\n".format(self.text_name)]
        for value_item in value:
            first = True
            for template_item in self.klass_template:
                for line in template_item.to_text(value_item).splitlines():
                    if first:
                        first = False
                        result.append(u"- {0}\n".format(line))
                    else:
                        result.append(u"  {0}\n".format(line))
        return u"".join(result)

    def focus_can_parse_line(self, line):
        return line.startswith(u"  ") or line.startswith(u"- ")

    def focus_parse_line(self, line, instance):
        if line.startswith(u"- "):
            if self.focus_cache is not None:
                if self.focused_template:
                    self.focused_template.focus_terminate(self.focus_cache)
                    self.focused_template = None
                self.focus_cache_array.append(self.focus_cache)
            self.focus_cache = self.klass()
        line = line[2:]

        if self.focused_template is not None:
            if self.focused_template.focus_can_parse_line(line):
                self.focused_template.focus_parse_line(line, self.focus_cache)
                return
            else:
                self.focused_template.focus_terminate(self.focus_cache)
                self.focused_template = None
        for item in self.klass_template:
            if item.can_parse_line(line):
                obtain_focus = item.parse_line(line, self.focus_cache)
                if obtain_focus:
                    self.focused_template = item
                return
        sys.stderr.write(u"Unknown input: {0}.\n".format(line))
        exit(1)

    def focus_terminate(self, instance):
        if self.focused_template is not None:
            self.focused_template.focus_terminate(self.focus_cache)
        if self.focus_cache is not None:
            self.focus_cache_array.append(self.focus_cache)
        setattr(instance, self.variable_name, self.focus_cache_array)

    def can_parse_line(self, line):
        return line.lower().startswith(self.parse_line_start_lower)

    def parse_line(self, line, instance):
        self.focus_cache = None
        self.focus_cache_array = []
        self.focused_template = None
        return True

    def is_valid(self, instance):
        value = self.value(instance)
        if not isinstance(value, list):
            return u"Expected list type of '{0}'.".format(self.variable_name)
        for value_item in value:
            if not isinstance(value_item, self.klass):
                return u"Expected {0} type of item in '{1}', but found {2}.".format(self.klass.__name__,
                                                                                    self.variable_name,
                                                                                    value_item.__class__.__name__)
            for template_item in self.klass_template:
                valid = template_item.is_valid(value_item)
                if valid != True:
                    return valid
        return True

    def database_table_name(self, table_prefix):
        return u"{0}_{1}".format(self.parent.database_table_name(table_prefix),
                                 self.variable_name)

    def to_database(self, instance, cursor, table_prefix):
        stored_items = [item for item in self.klass_template if item.database_is_stored]
        this_table_items = [item for item in stored_items if not item.database_has_separate_table]
        other_table_items = [item for item in stored_items if item.database_has_separate_table]

        value = self.value(instance)
        for value_item in value:
            cursor.execute(u"insert into {0} values (?, {1})".format(self.database_table_name(table_prefix),
                                                                     u", ".join([u"?" for item in this_table_items])),
                           [instance.id] + [item.value(value_item) for item in this_table_items])
            [item.to_database(value_item, cursor, table_prefix) for item in other_table_items]

    def database_create_table(self, cursor, table_prefix):
        stored_items = [item for item in self.klass_template if item.database_is_stored]
        this_table_items = [item for item in stored_items if not item.database_has_separate_table]
        other_table_items = [item for item in stored_items if item.database_has_separate_table]

        cursor.execute(u"create table if not exists {0} ({1}_id, {2})".format(self.database_table_name(table_prefix),
                                                                              self.parent.variable_name,
                                                                              u", ".join([item.variable_name for item in this_table_items])))
        if self.database_indexed:
            cursor.execute(u"create index if not exists {0}_{1}_id on {0} ({1}_id)".format(self.database_table_name(table_prefix),
                                                                                           self.parent.variable_name))
        for item in this_table_items:
            if item.database_indexed:
                cursor.execute(u"create index if not exists {0}_{1} on {0} ({1})".format(self.database_table_name(table_prefix),
                                                                                         item.variable_name))
        [item.database_create_table(cursor, table_prefix) for item in other_table_items]

class TemplateItemArrayInline(TemplateItem):
    def __init__(self, variable_name, text_name, type_, database_indexed):
        TemplateItem.__init__(self, variable_name, text_name,
                              database_is_stored=True, database_has_separate_table=True,
                              database_indexed=database_indexed)
        self.type = type_

    def to_text(self, instance):
        # Convert only valid values into text.
        valid = self.is_valid(instance)
        if valid != True:
            sys.stderr.write(u"{0}\n".format(valid))
            exit(1)
        value = self.value(instance)
        if len(value) == 0:
            return u""
        return u"{0}: {1}\n".format(self.text_name,
                                    u", ".join([unicode(item) for item in value]))

    def focus_can_parse_line(self, line):
        return False

    def focus_parse_line(self, line, instance):
        pass

    def focus_terminate(self, instance):
        pass

    def can_parse_line(self, line):
        return line.lower().startswith(self.parse_line_start_lower)

    def parse_line(self, line, instance):
        text = line[len(self.parse_line_start_lower):].strip()
        array = []
        for item in text.split(u','):
            item = item.strip()
            if len(item) > 0:
                array.append(self.type(item))
        setattr(instance, self.variable_name, array)
        return False

    def is_valid(self, instance):
        value = self.value(instance)
        if not isinstance(value, list):
            return u"Expected list type of '{0}'.".format(self.variable_name)
        for item in value:
            if not isinstance(item, self.type):
                return u"Unexpected type of item in '{0}'.".format(self.variable_name)
        return True

    def database_table_name(self, table_prefix):
        return u"{0}_{1}".format(self.parent.database_table_name(table_prefix),
                                 self.variable_name)

    def to_database(self, instance, cursor, table_prefix):
        value = self.value(instance)
        for item in value:
            cursor.execute(u"insert into {0} values (?, ?)".format(self.database_table_name(table_prefix)),
                           (instance.id, item))

    def database_create_table(self, cursor, table_prefix):
        cursor.execute(u"create table if not exists {0} ({1}_id, value)".format(self.database_table_name(table_prefix),
                                                                                self.parent.variable_name))
        if self.database_indexed:
            cursor.execute(u"create index if not exists {0}_{1}_id on {0} ({1}_id)".format(self.database_table_name(table_prefix),
                                                                                           self.parent.variable_name))
            cursor.execute(u"create index if not exists {0}_value on {0} (value)".format(self.database_table_name(table_prefix)))

class TemplateItemInt(TemplateItem):
    def __init__(self, variable_name, text_name, null, constraint, database_indexed):
        TemplateItem.__init__(self, variable_name, text_name,
                              database_is_stored=True, database_has_separate_table=False,
                              database_indexed=database_indexed)
        self.null = null
        self.constraint = constraint

    def to_text(self, instance):
        # Convert only valid values into text.
        valid = self.is_valid(instance)
        if valid != True:
            sys.stderr.write(u"{0}\n".format(valid))
            exit(1)
        value = self.value(instance)
        if value is None:
            return u""
        return u"{0}: {1}\n".format(self.text_name, value)

    def focus_can_parse_line(self, line):
        return False

    def focus_parse_line(self, line, instance):
        pass

    def focus_terminate(self, instance):
        pass

    def can_parse_line(self, line):
        return line.lower().startswith(self.parse_line_start_lower)

    def parse_line(self, line, instance):
        value = line[len(self.parse_line_start_lower):].strip()
        setattr(instance, self.variable_name, int(value))
        return False

    def is_valid(self, instance):
        value = self.value(instance)
        can_be_null = self.null
        if hasattr(can_be_null, u"__call__"):
            can_be_null = can_be_null(instance)
        if value is None and not can_be_null:
            return u"Missing value of '{0}' in {1}.".format(self.variable_name, instance.__class__.__name__)
        if value is not None:
            if not isinstance(value, int):
                return u"Expected int type of '{0}' in {1}, but it is a '{2}'.".format(self.variable_name,
                                                                                       instance.__class__.__name__,
                                                                                       value.__class__.__name__)
            if self.constraint is not None and not self.constraint(value, instance):
                return u"Unsatisfied constraint for '{0}' in {1}, its value is '{2}'.".format(self.variable_name,
                                                                                              instance.__class__.__name__, value)
        return True

class TemplateItemBoolean(TemplateItem):
    def __init__(self, variable_name, text_name, null, database_indexed):
        TemplateItem.__init__(self, variable_name, text_name,
                              database_is_stored=True, database_has_separate_table=False,
                              database_indexed=database_indexed)
        self.null = null

    def to_text(self, instance):
        # Convert only valid values into text.
        valid = self.is_valid(instance)
        if valid != True:
            sys.stderr.write(u"{0}\n".format(valid))
            exit(1)
        value = self.value(instance)
        if value is None:
            return u""
        return u"{0}: {1}\n".format(self.text_name, value)

    def focus_can_parse_line(self, line):
        return False

    def focus_parse_line(self, line, instance):
        pass

    def focus_terminate(self, instance):
        pass

    def can_parse_line(self, line):
        return line.lower().startswith(self.parse_line_start_lower)

    def parse_line(self, line, instance):
        value = line[len(self.parse_line_start_lower):].strip().lower()
        setattr(instance, self.variable_name, (value  == u"true" or value == u"yes" or value == u"1"))
        return False

    def is_valid(self, instance):
        value = self.value(instance)
        can_be_null = self.null
        if hasattr(can_be_null, u"__call__"):
            can_be_null = can_be_null(instance)
        if value is None and not can_be_null:
            return u"Missing value of '{0}' in {1}.".format(self.variable_name, instance.__class__.__name__)
        if value is not None and not isinstance(value, bool):
            return u"Expected bool type of '{0}' in {1}.".format(self.variable_name, instance.__class__.__name__)
        return True

class TemplateItemDateTime(TemplateItem):
    def __init__(self, variable_name, text_name, null, database_indexed):
        TemplateItem.__init__(self, variable_name, text_name,
                              database_is_stored=True, database_has_separate_table=False,
                              database_indexed=database_indexed)
        self.null = null

    def to_text(self, instance):
        # Convert only valid values into text.
        valid = self.is_valid(instance)
        if valid != True:
            sys.stderr.write(u"{0}\n".format(valid))
            exit(1)
        value = self.value(instance)
        if value is None:
            return u""
        return u"{0}: {1}\n".format(self.text_name, value.strftime(u"%Y-%m-%dT%H:%M:%S.%f%z"))

    def focus_can_parse_line(self, line):
        return False

    def focus_parse_line(self, line, instance):
        pass

    def focus_terminate(self, instance):
        pass

    def can_parse_line(self, line):
        return line.lower().startswith(self.parse_line_start_lower)

    def parse_line(self, line, instance):
        value = line[len(self.parse_line_start_lower):].strip()
        possible_formats = [u"%Y-%m-%dT%H:%M:%S.%f%z",
                            u"%Y-%m-%dT%H:%M:%S.%f",
                            u"%Y-%m-%dT%H:%M:%S%z",
                            u"%Y-%m-%dT%H:%M:%S",
                            u"%Y-%m-%d %H:%M:%S"]
        for fmt in possible_formats:
            try:
                value = datetime.datetime.strptime(value, fmt)
                break
            except ValueError:
                pass
        if not isinstance(value, datetime.datetime):
            sys.stderr.write(u"Failed to parse datetime string '{0}'.\n".format(value))
            exit(1)
        setattr(instance, self.variable_name, value)
        return False

    def is_valid(self, instance):
        value = self.value(instance)
        can_be_null = self.null
        if hasattr(can_be_null, u"__call__"):
            can_be_null = can_be_null(instance)
        if value is None and not can_be_null:
            return u"Missing value of '{0}' in {1}.".format(self.variable_name, instance.__class__.__name__)
        if value is not None and not isinstance(value, datetime.datetime):
            return u"Expected datetime type of '{0}' in {1}, but it is a '{2}'.".format(self.variable_name,
                                                                                        instance.__class__.__name__,
                                                                                        value.__class__.__name__)
        return True

class TemplateItemByteArray(TemplateItem):
    def __init__(self, variable_name, text_name, encoding, null, constraint):
        TemplateItem.__init__(self, variable_name, text_name,
                              database_is_stored=False, database_has_separate_table=False, database_indexed=False)
        self.encoding = encoding
        self.null = null
        self.constraint = constraint

    def to_text(self, instance):
        # Convert only valid values into text.
        valid = self.is_valid(instance)
        if valid != True:
            sys.stderr.write("{0}\n".format(valid))
            exit(1)
        value = self.value(instance)
        if value is None:
            return u""
        ptr = 0
        result = [u"{0}:\n".format(self.text_name)]
        if self.encoding == u"base64":
            while ptr <= len(value):
                line = base64.b64encode(value[ptr:ptr+2048])
                ptr += 2048
                result.append(u"  {0}\n".format(line))
        elif self.encoding == u"quoted_printable":
            value_qp = binascii.b2a_qp(value, header=False)
            for line in value_qp.splitlines():
                result.append(u"  {0}\n".format(line))
        else:
            sys.stderr.write(u"Invalid encoder '{0}'.\n".format(self.encoding))
            exit(1)
        return u"".join(result)

    def focus_can_parse_line(self, line):
        return line.startswith(u"  ")

    def focus_parse_line(self, line, instance):
        if self.encoding == u"base64":
            self.focus_cache.extend(base64.b64decode(line[2:]))
        elif self.encoding == u"quoted_printable":
            self.focus_cache.append(line[2:])
        else:
            sys.stderr.write(u"Invalid encoder '{0}'.\n".format(self.encoding))
            exit(1)

    def focus_terminate(self, instance):
        if self.encoding == u"quoted_printable":
            self.focus_cache = bytearray(binascii.a2b_qp("\n".join(self.focus_cache)))
        setattr(instance, self.variable_name, self.focus_cache)
        # Do not keep reference to this potentially huge object
        self.focus_cache = None

    def can_parse_line(self, line):
        return line.lower().startswith(self.parse_line_start_lower)

    def parse_line(self, line, instance):
        if self.encoding == u"base64":
            self.focus_cache = bytearray()
        elif self.encoding == u"quoted_printable":
            self.focus_cache = []
        else:
            sys.stderr.write(u"Invalid encoder '{0}'.\n".format(self.encoding))
            exit(1)
        return True

    def is_valid(self, instance):
        value = self.value(instance)
        can_be_null = self.null
        if hasattr(can_be_null, u"__call__"):
            can_be_null = can_be_null(instance)
        if value is None and not can_be_null:
            return u"Missing value of '{0}' in {1}.".format(self.variable_name, instance.__class__.__name__)
        if value is not None:
            if not isinstance(value, bytearray):
                return u"Expected bytearray type of '{0}' in {1}, but it is a '{2}'.".format(self.variable_name,
                                                                                             instance.__class__.__name__,
                                                                                             value.__class__.__name__)
            if self.constraint is not None and not self.constraint(value, instance):
                return u"Failed to validate the value of '{0}' in {1} by external validator.".format(self.variable_name,
                                                                                                     instance.__class__.__name__)
        return True

def toplevel(name, klass, klass_template):
    return TopLevelItem(name, klass, klass_template)

def int_signed(variable_name, text_name=None, null=False, database_indexed=False):
    return TemplateItemInt(variable_name, text_name, null=null, constraint=None, database_indexed=database_indexed)

def int_positive(variable_name, text_name=None, null=False, database_indexed=False):
    return TemplateItemInt(variable_name, text_name, null=null, constraint=lambda value,parent:value>0, database_indexed=database_indexed)

def int_unsigned(variable_name, text_name=None, null=False, database_indexed=False):
    return TemplateItemInt(variable_name, text_name, null=null, constraint=lambda value,parent:value>=0, database_indexed=database_indexed)

def string(variable_name, text_name=None, null=False, constraint=None, database_indexed=False):
    return TemplateItemString(variable_name, text_name, multiline=False, null=null, constraint=constraint, database_indexed=database_indexed)

def string_multiline(variable_name, text_name=None, null=False, constraint=None):
    return TemplateItemString(variable_name, text_name, multiline=True, null=null, constraint=constraint, database_indexed=False)

def boolean(variable_name, text_name=None, null=False, database_indexed=False):
    return TemplateItemBoolean(variable_name, text_name, null=null, database_indexed=database_indexed)

def array_string(variable_name, text_name=None, database_indexed=False):
    return TemplateItemArray(variable_name, text_name, type_=unicode, database_indexed=database_indexed)

def array_int(variable_name, text_name=None, database_indexed=False):
    return TemplateItemArray(variable_name, text_name, type_=int, database_indexed=database_indexed)

def array_dict(variable_name, klass, klass_template, text_name=None, database_indexed=False):
    return TemplateItemArrayDict(variable_name, text_name, klass, klass_template, database_indexed=database_indexed)

def array_inline_string(variable_name, text_name=None, database_indexed=False):
    return TemplateItemArrayInline(variable_name, text_name, type_=unicode, database_indexed=database_indexed)

def array_inline_int(variable_name, text_name=None, database_indexed=False):
    return TemplateItemArrayInline(variable_name, text_name, type_=int, database_indexed=database_indexed)

def date_time(variable_name, text_name=None, null=False, database_indexed=False):
    return TemplateItemDateTime(variable_name, text_name, null=null, database_indexed=database_indexed)

def bytearray_base64(variable_name, text_name=None, null=False, constraint=None):
    return TemplateItemByteArray(variable_name, text_name, encoding=u"base64", null=null, constraint=constraint)

def bytearray_quoted_printable(variable_name, text_name=None, null=False, constraint=None):
    return TemplateItemByteArray(variable_name, text_name, encoding=u"quoted_printable", null=null, constraint=constraint)
