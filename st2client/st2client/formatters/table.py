import json
import logging
from prettytable import PrettyTable

from st2client import formatters
from six.moves import zip


LOG = logging.getLogger(__name__)


class MultiColumnTable(formatters.Formatter):

    @classmethod
    def format(cls, entries, *args, **kwargs):
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
                        value = MultiColumnTable._get_field_value(value, name)
                        if type(value) is str:
                            break
                    values.append(value)
                else:
                    values.append(getattr(entry, field_name, ''))
            table.add_row(values)
        return table

    @staticmethod
    def _get_field_value(value, field_name):
        r_val = value.get(field_name, None)
        if r_val is None:
            return ''
        if isinstance(r_val, list) or isinstance(r_val, dict):
            return r_val if len(r_val) > 0 else ''
        return r_val


class PropertyValueTable(formatters.Formatter):

    @classmethod
    def format(cls, subject, *args, **kwargs):
        attributes = kwargs.get('attributes', None)
        display_order = kwargs.get('display_order',
                                   ['name', 'id', 'description'])
        if not attributes or 'all' in attributes:
            attributes = sorted([attr for attr in subject.__dict__
                                 if not attr.startswith('_')])
        for attr in display_order[::-1]:
            if attr in attributes:
                attributes.remove(attr)
                attributes = [attr] + attributes
        table = PrettyTable()
        table.field_names = ['Property', 'Value']
        table.max_width['Property'] = 20
        table.max_width['Value'] = 55
        table.padding_widht = 1
        table.align = 'l'
        table.valign = 't'
        for attribute in attributes:
            value = PropertyValueTable._get_attribute_value(subject, attribute)
            if type(value) is dict or type(value) is list:
                value = json.dumps(value, indent=4)
            table.add_row([attribute, value])
        return table

    @staticmethod
    def _get_attribute_value(subject, attribute):
        r_val = getattr(subject, attribute, None)
        if r_val is None:
            return ''
        if isinstance(r_val, list) or isinstance(r_val, dict):
            return r_val if len(r_val) > 0 else ''
        return r_val
