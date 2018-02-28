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
import re

import jsonschema
from jsonschema import Draft3Validator
from prompt_toolkit import prompt
from prompt_toolkit import token
from prompt_toolkit import validation

from st2client.exceptions.operations import OperationFailureException
from six.moves import range


POSITIVE_BOOLEAN = {'1', 'y', 'yes', 'true'}
NEGATIVE_BOOLEAN = {'0', 'n', 'no', 'nope', 'nah', 'false'}


class ReaderNotImplemented(OperationFailureException):
    pass


class DialogInterrupted(OperationFailureException):
    pass


class MuxValidator(validation.Validator):
    def __init__(self, validators, spec):
        super(MuxValidator, self).__init__()

        self.validators = validators
        self.spec = spec

    def validate(self, document):
        input = document.text

        for validator in self.validators:
            validator(input, self.spec)


class StringReader(object):
    def __init__(self, name, spec, prefix=None, secret=False, **kw):
        self.name = name
        self.spec = spec
        self.prefix = prefix or ''
        self.options = {
            'is_password': secret
        }

        self._construct_description()
        self._construct_template()
        self._construct_validators()

        self.options.update(kw)

    @staticmethod
    def condition(spec):
        return True

    @staticmethod
    def validate(input, spec):
        try:
            jsonschema.validate(input, spec, Draft3Validator)
        except jsonschema.ValidationError as e:
            raise validation.ValidationError(len(input), str(e))

    def read(self):
        message = self.template.format(self.prefix + self.name, **self.spec)
        response = prompt(message, **self.options)

        result = self.spec.get('default', None)

        if response:
            result = self._transform_response(response)

        return result

    def _construct_description(self):
        if 'description' in self.spec:
            def get_bottom_toolbar_tokens(cli):
                return [(token.Token.Toolbar, self.spec['description'])]

            self.options['get_bottom_toolbar_tokens'] = get_bottom_toolbar_tokens

    def _construct_template(self):
        self.template = u'{0}: '

        if 'default' in self.spec:
            self.template = u'{0} [{default}]: '

    def _construct_validators(self):
        self.options['validator'] = MuxValidator([self.validate], self.spec)

    def _transform_response(self, response):
        return response


class BooleanReader(StringReader):
    @staticmethod
    def condition(spec):
        return spec.get('type', None) == 'boolean'

    @staticmethod
    def validate(input, spec):
        if not input and (not spec.get('required', None) or spec.get('default', None)):
            return

        if input.lower() not in POSITIVE_BOOLEAN | NEGATIVE_BOOLEAN:
            raise validation.ValidationError(len(input),
                                             'Does not look like boolean. Pick from [%s]'
                                             % ', '.join(POSITIVE_BOOLEAN | NEGATIVE_BOOLEAN))

    def _construct_template(self):
        self.template = u'{0} (boolean)'

        if 'default' in self.spec:
            self.template += u' [{}]: '.format(self.spec.get('default') and 'y' or 'n')
        else:
            self.template += u': '

    def _transform_response(self, response):
        if response.lower() in POSITIVE_BOOLEAN:
            return True
        if response.lower() in NEGATIVE_BOOLEAN:
            return False

        # Hopefully, it will never happen
        raise OperationFailureException('Response neither positive no negative. '
                                        'Value have not been properly validated.')


class NumberReader(StringReader):
    @staticmethod
    def condition(spec):
        return spec.get('type', None) == 'number'

    @staticmethod
    def validate(input, spec):
        if input:
            try:
                input = float(input)
            except ValueError as e:
                raise validation.ValidationError(len(input), str(e))

            super(NumberReader, NumberReader).validate(input, spec)

    def _construct_template(self):
        self.template = u'{0} (float)'

        if 'default' in self.spec:
            self.template += u' [{default}]: '.format(default=self.spec.get('default'))
        else:
            self.template += u': '

    def _transform_response(self, response):
        return float(response)


class IntegerReader(StringReader):
    @staticmethod
    def condition(spec):
        return spec.get('type', None) == 'integer'

    @staticmethod
    def validate(input, spec):
        if input:
            try:
                input = int(input)
            except ValueError as e:
                raise validation.ValidationError(len(input), str(e))

            super(IntegerReader, IntegerReader).validate(input, spec)

    def _construct_template(self):
        self.template = u'{0} (integer)'

        if 'default' in self.spec:
            self.template += u' [{default}]: '.format(default=self.spec.get('default'))
        else:
            self.template += u': '

    def _transform_response(self, response):
        return int(response)


class SecretStringReader(StringReader):
    def __init__(self, *args, **kwargs):
        super(SecretStringReader, self).__init__(*args, secret=True, **kwargs)

    @staticmethod
    def condition(spec):
        return spec.get('secret', None)

    def _construct_template(self):
        self.template = u'{0} (secret)'

        if 'default' in self.spec:
            self.template += u' [{default}]: '.format(default=self.spec.get('default'))
        else:
            self.template += u': '


class EnumReader(StringReader):
    @staticmethod
    def condition(spec):
        return spec.get('enum', None)

    @staticmethod
    def validate(input, spec):
        if not input and (not spec.get('required', None) or spec.get('default', None)):
            return

        if not input.isdigit():
            raise validation.ValidationError(len(input), 'Not a number')

        enum = spec.get('enum')
        try:
            enum[int(input)]
        except IndexError:
            raise validation.ValidationError(len(input), 'Out of bounds')

    def _construct_template(self):
        self.template = u'{0}: '

        enum = self.spec.get('enum')
        for index, value in enumerate(enum):
            self.template += u'\n {} - {}'.format(index, value)

        num_options = len(enum)
        more = ''
        if num_options > 3:
            num_options = 3
            more = '...'
        options = [str(i) for i in range(0, num_options)]
        self.template += u'\nChoose from {}{}'.format(', '.join(options), more)

        if 'default' in self.spec:
            self.template += u' [{}]: '.format(enum.index(self.spec.get('default')))
        else:
            self.template += u': '

    def _transform_response(self, response):
        return self.spec.get('enum')[int(response)]


class ObjectReader(StringReader):

    @staticmethod
    def condition(spec):
        return spec.get('type', None) == 'object'

    def read(self):
        prefix = u'{}.'.format(self.name)

        result = InteractiveForm(self.spec.get('properties', {}),
                                 prefix=prefix, reraise=True).initiate_dialog()

        return result


class ArrayReader(StringReader):
    @staticmethod
    def condition(spec):
        return spec.get('type', None) == 'array'

    @staticmethod
    def validate(input, spec):
        if not input and (not spec.get('required', None) or spec.get('default', None)):
            return

        for m in re.finditer(r'[^, ]+', input):
            index, item = m.start(), m.group()
            try:
                StringReader.validate(item, spec.get('items', {}))
            except validation.ValidationError as e:
                raise validation.ValidationError(index, str(e))

    def read(self):
        item_type = self.spec.get('items', {}).get('type', 'string')

        if item_type not in ['string', 'integer', 'number', 'boolean']:
            message = 'Interactive mode does not support arrays of %s type yet' % item_type
            raise ReaderNotImplemented(message)

        result = super(ArrayReader, self).read()

        return result

    def _construct_template(self):
        self.template = u'{0} (comma-separated list)'

        if 'default' in self.spec:
            self.template += u' [{default}]: '.format(default=','.join(self.spec.get('default')))
        else:
            self.template += u': '

    def _transform_response(self, response):
        return [item.strip() for item in response.split(',')]


class ArrayObjectReader(StringReader):
    @staticmethod
    def condition(spec):
        return spec.get('type', None) == 'array' and spec.get('items', {}).get('type') == 'object'

    def read(self):
        results = []
        properties = self.spec.get('items', {}).get('properties', {})
        message = '~~~ Would you like to add another item to  "%s" array / list?' % self.name

        is_continue = True
        index = 0
        while is_continue:
            prefix = u'{name}[{index}].'.format(name=self.name, index=index)
            results.append(InteractiveForm(properties,
                                           prefix=prefix,
                                           reraise=True).initiate_dialog())

            index += 1
            if Question(message, {'default': 'y'}).read() != 'y':
                is_continue = False

        return results


class ArrayEnumReader(EnumReader):
    def __init__(self, name, spec, prefix=None):
        self.items = spec.get('items', {})

        super(ArrayEnumReader, self).__init__(name, spec, prefix)

    @staticmethod
    def condition(spec):
        return spec.get('type', None) == 'array' and 'enum' in spec.get('items', {})

    @staticmethod
    def validate(input, spec):
        if not input and (not spec.get('required', None) or spec.get('default', None)):
            return

        for m in re.finditer(r'[^, ]+', input):
            index, item = m.start(), m.group()
            try:
                EnumReader.validate(item, spec.get('items', {}))
            except validation.ValidationError as e:
                raise validation.ValidationError(index, str(e))

    def _construct_template(self):
        self.template = u'{0}: '

        enum = self.items.get('enum')
        for index, value in enumerate(enum):
            self.template += u'\n {} - {}'.format(index, value)

        num_options = len(enum)
        more = ''
        if num_options > 3:
            num_options = 3
            more = '...'
        options = [str(i) for i in range(0, num_options)]
        self.template += u'\nChoose from {}{}'.format(', '.join(options), more)

        if 'default' in self.spec:
            default_choises = [str(enum.index(item)) for item in self.spec.get('default')]
            self.template += u' [{}]: '.format(', '.join(default_choises))
        else:
            self.template += u': '

    def _transform_response(self, response):
        result = []

        for i in (item.strip() for item in response.split(',')):
            if i:
                result.append(self.items.get('enum')[int(i)])

        return result


class InteractiveForm(object):
    readers = [
        EnumReader,
        BooleanReader,
        NumberReader,
        IntegerReader,
        ObjectReader,
        ArrayEnumReader,
        ArrayObjectReader,
        ArrayReader,
        SecretStringReader,
        StringReader
    ]

    def __init__(self, schema, prefix=None, reraise=False):
        self.schema = schema
        self.prefix = prefix
        self.reraise = reraise

    def initiate_dialog(self):
        result = {}

        try:
            for field in self.schema:
                try:
                    result[field] = self._read_field(field)
                except ReaderNotImplemented as e:
                    print('%s. Skipping...' % str(e))
        except DialogInterrupted:
            if self.reraise:
                raise
            print('Dialog interrupted.')

        return result

    def _read_field(self, field):
        spec = self.schema[field]

        reader = None

        for Reader in self.readers:
            if Reader.condition(spec):
                reader = Reader(field, spec, prefix=self.prefix)
                break

        if not reader:
            raise ReaderNotImplemented('No reader for the field spec')

        try:
            return reader.read()
        except KeyboardInterrupt:
            raise DialogInterrupted()


class Question(StringReader):
    def __init__(self, message, spec=None):
        if not spec:
            spec = {}

        super(Question, self).__init__(message, spec)
