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

import json
import math
import logging

from prettytable import PrettyTable
from six.moves import zip

from st2client import formatters
from st2client.utils import strutil
from st2client.utils.terminal import get_terminal_size


LOG = logging.getLogger(__name__)

# Minimum width for the ID to make sure the ID column doesn't wrap across
# multiple lines
MIN_ID_COL_WIDTH = 26
DEFAULT_ATTRIBUTE_DISPLAY_ORDER = ['id', 'name', 'pack', 'description']


class MultiColumnTable(formatters.Formatter):

    @classmethod
    def format(cls, entries, *args, **kwargs):
        attributes = kwargs.get('attributes', [])
        attribute_transform_functions = kwargs.get('attribute_transform_functions', {})
        widths = kwargs.get('widths', [])
        widths = widths or []

        if not widths and attributes:
            # Dynamically calculate column size based on the terminal size
            lines, cols = get_terminal_size()

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
            for index in range(0, len(attributes)):
                if index == 0:
                    widths.append(first_col_width)
                else:
                    widths.append(col_width)

        if not attributes or 'all' in attributes:
            attributes = sorted([attr for attr in entries[0].__dict__
                                 if not attr.startswith('_')])

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
                    value = strutil.unescape(value)
                    values.append(value)
                else:
                    value = cls._get_simple_field_value(entry, field_name)
                    transform_function = attribute_transform_functions.get(field_name,
                                                                          lambda value: value)
                    value = transform_function(value=value)
                    value = strutil.unescape(value)
                    values.append(value)
            table.add_row(values)
        return table

    @staticmethod
    def _get_simple_field_value(entry, field_name):
        """
        Format a value for a simple field.
        """
        value = getattr(entry, field_name, '')
        if isinstance(value, (list, tuple)):
            if len(value) == 0:
                value = ''
            elif isinstance(value[0], (str, unicode)):
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
        width = minimum_width
        max_width = len(max(values, key=len))
        return max_width if max_width > width else width


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

            value = strutil.unescape(value)
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
