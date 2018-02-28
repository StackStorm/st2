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
import logging
import mock
import re
import unittest2

import prompt_toolkit
from prompt_toolkit.document import Document
from six.moves import StringIO

from st2client.utils import interactive
import six


LOG = logging.getLogger(__name__)


class TestInteractive(unittest2.TestCase):

    def assertPromptMessage(self, prompt_mock, message, msg=None):
        self.assertEqual(prompt_mock.call_args[0], (message,), msg)

    def assertPromptDescription(self, prompt_mock, message, msg=None):
        toolbar_factory = prompt_mock.call_args[1]['get_bottom_toolbar_tokens']
        self.assertEqual(toolbar_factory(None)[0][1], message, msg)

    def assertPromptValidate(self, prompt_mock, value):
        validator = prompt_mock.call_args[1]['validator']

        validator.validate(Document(text=six.text_type(value)))

    def assertPromptPassword(self, prompt_mock, value, msg=None):
        self.assertEqual(prompt_mock.call_args[1]['is_password'], value, msg)

    def test_interactive_form(self):
        reader = mock.MagicMock()
        Reader = mock.MagicMock(return_value=reader)
        Reader.condition = mock.MagicMock(return_value=True)

        schema = {
            'string': {
                'type': 'string'
            }
        }

        with mock.patch.object(interactive.InteractiveForm, 'readers', [Reader]):
            interactive.InteractiveForm(schema).initiate_dialog()

        Reader.condition.assert_called_once_with(schema['string'])
        reader.read.assert_called_once_with()

    def test_interactive_form_no_match(self):
        reader = mock.MagicMock()
        Reader = mock.MagicMock(return_value=reader)
        Reader.condition = mock.MagicMock(return_value=False)

        schema = {
            'string': {
                'type': 'string'
            }
        }

        with mock.patch.object(interactive.InteractiveForm, 'readers', [Reader]):
            interactive.InteractiveForm(schema).initiate_dialog()

        Reader.condition.assert_called_once_with(schema['string'])
        reader.read.assert_not_called()

    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_interactive_form_interrupted(self, stdout_mock):
        reader = mock.MagicMock()
        Reader = mock.MagicMock(return_value=reader)
        Reader.condition = mock.MagicMock(return_value=True)
        reader.read = mock.MagicMock(side_effect=KeyboardInterrupt)

        schema = {
            'string': {
                'type': 'string'
            }
        }

        with mock.patch.object(interactive.InteractiveForm, 'readers', [Reader]):
            interactive.InteractiveForm(schema).initiate_dialog()

        self.assertEquals(stdout_mock.getvalue(), 'Dialog interrupted.\n')

    def test_interactive_form_interrupted_reraised(self):
        reader = mock.MagicMock()
        Reader = mock.MagicMock(return_value=reader)
        Reader.condition = mock.MagicMock(return_value=True)
        reader.read = mock.MagicMock(side_effect=KeyboardInterrupt)

        schema = {
            'string': {
                'type': 'string'
            }
        }

        with mock.patch.object(interactive.InteractiveForm, 'readers', [Reader]):
            self.assertRaises(interactive.DialogInterrupted,
                              interactive.InteractiveForm(schema, reraise=True).initiate_dialog)

    @mock.patch.object(interactive, 'prompt')
    def test_stringreader(self, prompt_mock):
        spec = {
            'description': 'some description',
            'default': 'hey'
        }
        Reader = interactive.StringReader('some', spec)

        prompt_mock.return_value = 'stuff'
        result = Reader.read()

        self.assertEqual(result, 'stuff')
        self.assertPromptMessage(prompt_mock, 'some [hey]: ')
        self.assertPromptDescription(prompt_mock, 'some description')
        self.assertPromptValidate(prompt_mock, 'stuff')

        prompt_mock.return_value = ''
        result = Reader.read()

        self.assertEqual(result, 'hey')
        self.assertPromptValidate(prompt_mock, '')

    @mock.patch.object(interactive, 'prompt')
    def test_booleanreader(self, prompt_mock):
        spec = {
            'description': 'some description',
            'default': False
        }
        Reader = interactive.BooleanReader('some', spec)

        prompt_mock.return_value = 'y'
        result = Reader.read()

        self.assertEqual(result, True)
        self.assertPromptMessage(prompt_mock, 'some (boolean) [n]: ')
        self.assertPromptDescription(prompt_mock, 'some description')
        self.assertPromptValidate(prompt_mock, 'y')
        self.assertRaises(prompt_toolkit.validation.ValidationError,
                          self.assertPromptValidate, prompt_mock, 'some')

        prompt_mock.return_value = ''
        result = Reader.read()

        self.assertEqual(result, False)
        self.assertPromptValidate(prompt_mock, '')

    @mock.patch.object(interactive, 'prompt')
    def test_numberreader(self, prompt_mock):
        spec = {
            'description': 'some description',
            'default': 3.2
        }
        Reader = interactive.NumberReader('some', spec)

        prompt_mock.return_value = '5.3'
        result = Reader.read()

        self.assertEqual(result, 5.3)
        self.assertPromptMessage(prompt_mock, 'some (float) [3.2]: ')
        self.assertPromptDescription(prompt_mock, 'some description')
        self.assertPromptValidate(prompt_mock, '5.3')
        self.assertRaises(prompt_toolkit.validation.ValidationError,
                          self.assertPromptValidate, prompt_mock, 'some')

        prompt_mock.return_value = ''
        result = Reader.read()

        self.assertEqual(result, 3.2)
        self.assertPromptValidate(prompt_mock, '')

    @mock.patch.object(interactive, 'prompt')
    def test_integerreader(self, prompt_mock):
        spec = {
            'description': 'some description',
            'default': 3
        }
        Reader = interactive.IntegerReader('some', spec)

        prompt_mock.return_value = '5'
        result = Reader.read()

        self.assertEqual(result, 5)
        self.assertPromptMessage(prompt_mock, 'some (integer) [3]: ')
        self.assertPromptDescription(prompt_mock, 'some description')
        self.assertPromptValidate(prompt_mock, '5')
        self.assertRaises(prompt_toolkit.validation.ValidationError,
                          self.assertPromptValidate, prompt_mock, '5.3')

        prompt_mock.return_value = ''
        result = Reader.read()

        self.assertEqual(result, 3)
        self.assertPromptValidate(prompt_mock, '')

    @mock.patch.object(interactive, 'prompt')
    def test_secretstringreader(self, prompt_mock):
        spec = {
            'description': 'some description',
            'default': 'hey'
        }
        Reader = interactive.SecretStringReader('some', spec)

        prompt_mock.return_value = 'stuff'
        result = Reader.read()

        self.assertEqual(result, 'stuff')
        self.assertPromptMessage(prompt_mock, 'some (secret) [hey]: ')
        self.assertPromptDescription(prompt_mock, 'some description')
        self.assertPromptValidate(prompt_mock, 'stuff')
        self.assertPromptPassword(prompt_mock, True)

        prompt_mock.return_value = ''
        result = Reader.read()

        self.assertEqual(result, 'hey')
        self.assertPromptValidate(prompt_mock, '')

    @mock.patch.object(interactive, 'prompt')
    def test_enumreader(self, prompt_mock):
        spec = {
            'enum': ['some', 'thing', 'else'],
            'description': 'some description',
            'default': 'thing'
        }
        Reader = interactive.EnumReader('some', spec)

        prompt_mock.return_value = '2'
        result = Reader.read()

        self.assertEqual(result, 'else')
        message = 'some: \n 0 - some\n 1 - thing\n 2 - else\nChoose from 0, 1, 2 [1]: '
        self.assertPromptMessage(prompt_mock, message)
        self.assertPromptDescription(prompt_mock, 'some description')
        self.assertPromptValidate(prompt_mock, '0')
        self.assertRaises(prompt_toolkit.validation.ValidationError,
                          self.assertPromptValidate, prompt_mock, 'some')
        self.assertRaises(prompt_toolkit.validation.ValidationError,
                          self.assertPromptValidate, prompt_mock, '5')

        prompt_mock.return_value = ''
        result = Reader.read()

        self.assertEqual(result, 'thing')
        self.assertPromptValidate(prompt_mock, '')

    @mock.patch.object(interactive, 'prompt')
    def test_arrayreader(self, prompt_mock):
        spec = {
            'description': 'some description',
            'default': ['a', 'b']
        }
        Reader = interactive.ArrayReader('some', spec)

        prompt_mock.return_value = 'some,thing,else'
        result = Reader.read()

        self.assertEqual(result, ['some', 'thing', 'else'])
        self.assertPromptMessage(prompt_mock, 'some (comma-separated list) [a,b]: ')
        self.assertPromptDescription(prompt_mock, 'some description')
        self.assertPromptValidate(prompt_mock, 'some,thing,else')

        prompt_mock.return_value = ''
        result = Reader.read()

        self.assertEqual(result, ['a', 'b'])
        self.assertPromptValidate(prompt_mock, '')

    @mock.patch.object(interactive, 'prompt')
    def test_arrayreader_ends_with_comma(self, prompt_mock):
        spec = {
            'description': 'some description',
            'default': ['a', 'b']
        }
        Reader = interactive.ArrayReader('some', spec)

        prompt_mock.return_value = 'some,thing,else,'
        result = Reader.read()

        self.assertEqual(result, ['some', 'thing', 'else', ''])
        self.assertPromptMessage(prompt_mock, 'some (comma-separated list) [a,b]: ')
        self.assertPromptDescription(prompt_mock, 'some description')
        self.assertPromptValidate(prompt_mock, 'some,thing,else,')

    @mock.patch.object(interactive, 'prompt')
    def test_arrayenumreader(self, prompt_mock):
        spec = {
            'items': {
                'enum': ['a', 'b', 'c', 'd', 'e']
            },
            'description': 'some description',
            'default': ['a', 'b']
        }
        Reader = interactive.ArrayEnumReader('some', spec)

        prompt_mock.return_value = '0,2,4'
        result = Reader.read()

        self.assertEqual(result, ['a', 'c', 'e'])
        message = 'some: \n 0 - a\n 1 - b\n 2 - c\n 3 - d\n 4 - e\nChoose from 0, 1, 2... [0, 1]: '
        self.assertPromptMessage(prompt_mock, message)
        self.assertPromptDescription(prompt_mock, 'some description')
        self.assertPromptValidate(prompt_mock, '0,2,4')

        prompt_mock.return_value = ''
        result = Reader.read()

        self.assertEqual(result, ['a', 'b'])
        self.assertPromptValidate(prompt_mock, '')

    @mock.patch.object(interactive, 'prompt')
    def test_arrayenumreader_ends_with_comma(self, prompt_mock):
        spec = {
            'items': {
                'enum': ['a', 'b', 'c', 'd', 'e']
            },
            'description': 'some description',
            'default': ['a', 'b']
        }
        Reader = interactive.ArrayEnumReader('some', spec)

        prompt_mock.return_value = '0,2,4,'
        result = Reader.read()

        self.assertEqual(result, ['a', 'c', 'e'])
        message = 'some: \n 0 - a\n 1 - b\n 2 - c\n 3 - d\n 4 - e\nChoose from 0, 1, 2... [0, 1]: '
        self.assertPromptMessage(prompt_mock, message)
        self.assertPromptDescription(prompt_mock, 'some description')
        self.assertPromptValidate(prompt_mock, '0,2,4,')

    @mock.patch.object(interactive, 'prompt')
    def test_arrayobjectreader(self, prompt_mock):
        spec = {
            'items': {
                'type': 'object',
                'properties': {
                    'foo': {
                        'type': 'string',
                        'description': 'some description',
                    },
                    'bar': {
                        'type': 'string',
                        'description': 'some description',
                    }
                }
            },
            'description': 'some description',
        }
        Reader = interactive.ArrayObjectReader('some', spec)

        # To emulate continuing setting, this flag variable is needed
        self.is_continued = False

        def side_effect(msg, **kwargs):
            if re.match(r'^~~~ Would you like to add another item to.*', msg):
                # prompt requires the input to judge continuing setting, or not
                if not self.is_continued:
                    # continuing the configuration only once
                    self.is_continued = True
                    return ''
                else:
                    # finishing to configuration
                    return 'n'
            else:
                # prompt requires the input of property value in the object
                return 'value'

        prompt_mock.side_effect = side_effect
        results = Reader.read()

        self.assertEqual(len(results), 2)
        self.assertTrue(all([len(list(x.keys())) == 2 for x in results]))
        self.assertTrue(all(['foo' in x and 'bar' in x for x in results]))
