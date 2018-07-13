# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import json
import math
import logging
import sys

import six
from prettytable import PrettyTable
from six.moves import zip
from six.moves import range

from st2client import formatters
from st2client.utils import strutil
from st2client.utils.terminal import get_terminal_size_columns


LOG = logging.getLogger(__name__)

# Minimum width for the ID to make sure the ID column doesn't wrap across
# multiple lines
MIN_ID_COL_WIDTH = 26

# Minimum width for a column
MIN_COL_WIDTH = 5

# Default attribute display order to use if one is not provided
DEFAULT_ATTRIBUTE_DISPLAY_ORDER = ['id', 'name', 'pack', 'description']

# Attributes which contain bash escape sequences - we can't split those across multiple lines
# since things would break
COLORIZED_ATTRIBUTES = {
    'status': {
        'col_width': 24  # Note: len('succeed' + ' (XXXX elapsed)') <= 24
    }
}


class MultiColumnTable(formatters.Formatter):

    def __init__(self):
        self._table_width = 0

    @classmethod
    def format(cls, entries, *args, **kwargs):
        attributes = kwargs.get('attributes', [])
        attribute_transform_functions = kwargs.get('attribute_transform_functions', {})
        widths = kwargs.get('widths', [])
        widths = widths or []

        if not widths and attributes:
            # Dynamically calculate column size based on the terminal size
            cols = get_terminal_size_columns()

            if attributes[0] == 'id':
                # consume iterator and save as entries so collection is accessible later.
                entries = [e for e in entries]
                # first column contains id, make sure it's not broken up
                first_col_width = cls._get_required_column_width(values=[e.id for e in entries],
                                                                 minimum_width=MIN_ID_COL_WIDTH)
                cols = (cols - first_col_width)
                col_width = int(math.floor((cols / len(attributes))))
            else:
                col_width = int(math.floor((cols / len(attributes))))
                first_col_width = col_width
            widths = []
            subtract = 0
            for index in range(0, len(attributes)):
                attribute_name = attributes[index]

                if index == 0:
                    widths.append(first_col_width)
                    continue

                if attribute_name in COLORIZED_ATTRIBUTES:
                    current_col_width = COLORIZED_ATTRIBUTES[attribute_name]['col_width']
                    subtract += (current_col_width - col_width)
                else:
                    # Make sure we subtract the added width from the last column so we account
                    # for the fixed width columns and make sure table is not wider than the
                    # terminal width.
                    if index == (len(attributes) - 1) and subtract:
                        current_col_width = (col_width - subtract)

                        if current_col_width <= MIN_COL_WIDTH:
                            # Make sure column width is always grater than MIN_COL_WIDTH
                            current_col_width = MIN_COL_WIDTH
                    else:
                        current_col_width = col_width

                widths.append(current_col_width)

        if not attributes or 'all' in attributes:
            entries = list(entries) if entries else []

            if len(entries) >= 1:
                attributes = list(entries[0].__dict__.keys())
                attributes = sorted([attr for attr in attributes if not attr.startswith('_')])
            else:
                # There are no entries so we can't infer available attributes
                attributes = []

        # Determine table format.
        if len(attributes) == len(widths):
            # Customize width for each column.
            columns = zip(attributes, widths)
        else:
            # If only 1 width value is provided then
            # apply it to all columns else fix at 28.
            width = widths[0] if len(widths) == 1 else 28
            columns = zip(attributes,
                          [width for i in range(0, len(attributes))])

        # Format result to table.
        table = PrettyTable()
        for column in columns:
            table.field_names.append(column[0])
            table.max_width[column[0]] = column[1]
        table.padding_width = 1
        table.align = 'l'
        table.valign = 't'
        for entry in entries:
            # TODO: Improve getting values of nested dict.
            values = []
            for field_name in table.field_names:
                if '.' in field_name:
                    field_names = field_name.split('.')
                    value = getattr(entry, field_names.pop(0), {})
                    for name in field_names:
                        value = cls._get_field_value(value, name)
                        if type(value) is str:
                            break
                    value = strutil.strip_carriage_returns(strutil.unescape(value))
                    values.append(value)
                else:
                    value = cls._get_simple_field_value(entry, field_name)
                    transform_function = attribute_transform_functions.get(field_name,
                                                                           lambda value: value)
                    value = transform_function(value=value)
                    value = strutil.strip_carriage_returns(strutil.unescape(value))
                    values.append(value)
            table.add_row(values)

        # width for the note
        try:
            cls.table_width = len(table.get_string().split("\n")[0])
        except IndexError:
            cls.table_width = 0

        return table

    @property
    def table_width(self):
        return self._table_width

    @table_width.setter
    def table_width(self, value):
        self._table_width = value

    @staticmethod
    def _get_simple_field_value(entry, field_name):
        """
        Format a value for a simple field.
        """
        value = getattr(entry, field_name, '')
        if isinstance(value, (list, tuple)):
            if len(value) == 0:
                value = ''
            elif isinstance(value[0], (str, six.text_type)):
                # List contains simple string values, format it as comma
                # separated string
                value = ', '.join(value)

        return value

    @staticmethod
    def _get_field_value(value, field_name):
        r_val = value.get(field_name, None)
        if r_val is None:
            return ''

        if isinstance(r_val, list) or isinstance(r_val, dict):
            return r_val if len(r_val) > 0 else ''
        return r_val

    @staticmethod
    def _get_friendly_column_name(name):
        if not name:
            return None

        friendly_name = name.replace('_', ' ').replace('.', ' ').capitalize()
        return friendly_name

    @staticmethod
    def _get_required_column_width(values, minimum_width=0):
        max_width = len(max(values, key=len)) if values else minimum_width
        return max_width if max_width > minimum_width else minimum_width


class PropertyValueTable(formatters.Formatter):

    @classmethod
    def format(cls, subject, *args, **kwargs):
        attributes = kwargs.get('attributes', None)
        attribute_display_order = kwargs.get('attribute_display_order',
                                             DEFAULT_ATTRIBUTE_DISPLAY_ORDER)
        attribute_transform_functions = kwargs.get('attribute_transform_functions', {})

        if not attributes or 'all' in attributes:
            attributes = sorted([attr for attr in subject.__dict__
                                 if not attr.startswith('_')])

        for attr in attribute_display_order[::-1]:
            if attr in attributes:
                attributes.remove(attr)
                attributes = [attr] + attributes
        table = PrettyTable()
        table.field_names = ['Property', 'Value']
        table.max_width['Property'] = 20
        table.max_width['Value'] = 60
        table.padding_width = 1
        table.align = 'l'
        table.valign = 't'

        for attribute in attributes:
            if '.' in attribute:
                field_names = attribute.split('.')
                value = cls._get_attribute_value(subject, field_names.pop(0))
                for name in field_names:
                    value = cls._get_attribute_value(value, name)
                    if type(value) is str:
                        break
            else:
                value = cls._get_attribute_value(subject, attribute)

            transform_function = attribute_transform_functions.get(attribute,
                                                                   lambda value: value)
            value = transform_function(value=value)

            if type(value) is dict or type(value) is list:
                value = json.dumps(value, indent=4)

            value = strutil.strip_carriage_returns(strutil.unescape(value))
            table.add_row([attribute, value])
        return table

    @staticmethod
    def _get_attribute_value(subject, attribute):
        if isinstance(subject, dict):
            r_val = subject.get(attribute, None)
        else:
            r_val = getattr(subject, attribute, None)
        if r_val is None:
            return ''
        if isinstance(r_val, list) or isinstance(r_val, dict):
            return r_val if len(r_val) > 0 else ''
        return r_val


class SingleRowTable(object):
    @staticmethod
    def note_box(entity, limit):
        if limit <= 0:
            return None
        elif limit == 1:

            if entity == "inquiries":
                entity = "inquiry"
            else:
                entity = entity[:-1]

            message = "Note: Only one %s is displayed. Use -n/--last flag for more results." \
                % entity
        else:
            message = "Note: Only first %s %s are displayed. Use -n/--last flag for more results."\
                % (limit, entity)
        # adding default padding
        message_length = len(message) + 3
        m = MultiColumnTable()
        if m.table_width > message_length:
            note = PrettyTable([""], right_padding_width=(m.table_width - message_length))
        else:
            note = PrettyTable([""])
        note.header = False
        note.add_row([message])
        sys.stderr.write((str(note) + '\n'))
        return
