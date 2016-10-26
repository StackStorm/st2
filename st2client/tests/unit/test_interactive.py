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

import logging
import mock
from StringIO import StringIO
import unittest2

from st2client.utils import interactive


LOG = logging.getLogger(__name__)


class TestInteractive(unittest2.TestCase):

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
