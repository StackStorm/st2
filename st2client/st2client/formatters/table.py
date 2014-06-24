# -*- coding: utf-8 -*-
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import json
import logging
from prettytable import PrettyTable

from st2client import formatters


LOG = logging.getLogger(__name__)


class MultiColumnTable(formatters.Formatter):

    @classmethod
    def format(self, entries, *args, **kwargs):
        attributes = kwargs.get('attributes', [])
        widths = kwargs.get('widths', [])

        if not attributes or 'all' in attributes:
            attributes = sorted([attr for attr in entries[0].__dict__
                                 if not attr.startswith('_')])

        # Determine table format.
        if len(attributes) == len(widths):
            # Customize width for each column.
            columns = zip(attributes, widths)
        else:
            # If only 1 width value is provided then
            # apply it to all columns else fix at 25.
            width = widths[0] if len(widths) == 1 else 25
            columns = zip(attributes,
                          [width for i in range(0, len(attributes))])

        # Format result to table.
        table = PrettyTable()
        table.field_names = [column[0] for column in columns]
        for column in columns:
            table.max_width[column[0]] = column[1]
        table.padding_width = 1
        table.align = 'l'
        for entry in entries:
            table.add_row([getattr(entry, field_name, '')
                           for field_name in table.field_names])
        return table


class PropertyValueTable(formatters.Formatter):

    @classmethod
    def format(self, subject, *args, **kwargs):
        attributes = kwargs.get('attributes', None)
        if not attributes or 'all' in attributes:
            attributes = sorted([attr for attr in subject.__dict__
                                 if not attr.startswith('_')])
        table = PrettyTable()
        table.field_names = ['Property', 'Value']
        table.max_width['Property'] = 20
        table.max_width['Value'] = 55
        table.padding_widht = 1
        table.align = 'l'
        for attribute in attributes:
            value = getattr(subject, attribute, '')
            if type(value) is dict:
                value = json.dumps(value, indent=4)
            elif type(value) is list:
                value = ", ".join(value)
            table.add_row([attribute, value])
        return table
