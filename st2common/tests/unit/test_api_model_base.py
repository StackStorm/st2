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

import mock
import pecan
import unittest
from webob import exc

from st2common.models.api import base


class FakeModel(base.BaseAPI):
    model = None
    schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "properties": {
            "a": {"type": "string"}
        },
        "additionalProperties": False
    }


@mock.patch.object(pecan, 'request', mock.MagicMock(json={'a': 'b'}))
@mock.patch.object(pecan, 'response', mock.MagicMock())
class TestAPIModelBase(unittest.TestCase):

    def setUp(self):
        super(TestAPIModelBase, self).setUp()
        self.f = mock.MagicMock(__name__="Name")

    def test_expose_decorator(self):
        @base.jsexpose()
        def f(self, *args, **kwargs):
            self.f(self, args, kwargs)

        f(self)

        self.f.assert_called_once_with(self, (), {})

    def test_expose_argument(self):
        @base.jsexpose()
        def f(self, id, *args, **kwargs):
            self.f(self, id, args, kwargs)

        f(self, '11')

        self.f.assert_called_once_with(self, '11', (), {})

    def test_expose_argument_unused(self):
        @base.jsexpose()
        def f(self, *args, **kwargs):
            self.f(self, args, kwargs)

        f(self, '11')

        self.f.assert_called_once_with(self, ('11',), {})

    def test_expose_argument_type_casting(self):
        @base.jsexpose(arg_types=[int])
        def f(self, id, *args, **kwargs):
            self.f(self, id, args, kwargs)

        f(self, '11')

        self.f.assert_called_once_with(self, 11, (), {})

    def test_expose_argument_with_default(self):
        @base.jsexpose(arg_types=[int])
        def f(self, id, some=None, *args, **kwargs):
            self.f(self, id, some, args, kwargs)

        f(self, '11')

        self.f.assert_called_once_with(self, 11, None, (), {})

    def test_expose_kv_unused(self):
        @base.jsexpose([int, int, str])
        def f(self, id, *args, **kwargs):
            self.f(self, id, args, kwargs)

        f(self, '11', number='7', name="fox")

        self.f.assert_called_once_with(self, 11, (), {'number': '7', 'name': 'fox'})

    def test_expose_kv_type_casting(self):
        @base.jsexpose([int, int, str])
        def f(self, id, number, name, *args, **kwargs):
            self.f(self, id, number, name, args, kwargs)

        f(self, '11', number='7', name="fox")

        self.f.assert_called_once_with(self, 11, 7, 'fox', (), {})

    def test_expose_body_unused(self):
        APIModelMock = mock.MagicMock()

        @base.jsexpose(body_cls=APIModelMock)
        def f(self, *args, **kwargs):
            self.f(self, args, kwargs)

        f(self)

        APIModelMock.assert_called_once_with(a='b')
        self.f.assert_called_once_with(self, (APIModelMock().validate(),), {})

    def test_expose_body(self):
        APIModelMock = mock.MagicMock()

        @base.jsexpose(body_cls=APIModelMock)
        def f(self, body, *args, **kwargs):
            self.f(self, body, args, kwargs)

        f(self)

        APIModelMock.assert_called_once_with(a='b')
        self.f.assert_called_once_with(self, APIModelMock().validate(), (), {})

    def test_expose_body_and_arguments_unused(self):
        APIModelMock = mock.MagicMock()

        @base.jsexpose(body_cls=APIModelMock)
        def f(self, body, *args, **kwargs):
            self.f(self, body, args, kwargs)

        f(self, '11')

        APIModelMock.assert_called_once_with(a='b')
        self.f.assert_called_once_with(self, APIModelMock().validate(), ('11', ), {})

    def test_expose_body_and_arguments_type_casting(self):
        APIModelMock = mock.MagicMock()

        @base.jsexpose(arg_types=[int], body_cls=APIModelMock)
        def f(self, body, id, *args, **kwargs):
            self.f(self, body, id, args, kwargs)

        f(self, '11')

        APIModelMock.assert_called_once_with(a='b')
        self.f.assert_called_once_with(self, APIModelMock().validate(), 11, (), {})

    @unittest.skip
    def test_expose_body_and_typed_arguments_unused(self):
        APIModelMock = mock.MagicMock()

        @base.jsexpose(arg_types=[int], body_cls=APIModelMock)
        def f(self, body, id, *args, **kwargs):
            self.f(self, body, id, args, kwargs)

        f(self, '11', 'some')

        APIModelMock.assert_called_once_with(a='b')
        self.f.assert_called_once_with(self, APIModelMock().validate(), 11, ('some', ), {})

    @unittest.skip
    def test_expose_body_and_typed_kw_unused(self):
        APIModelMock = mock.MagicMock()

        @base.jsexpose(arg_types=[int], body_cls=APIModelMock)
        def f(self, body, id, *args, **kwargs):
            self.f(self, body, id, args, kwargs)

        f(self, id='11')

        APIModelMock.assert_called_once_with(a='b')
        self.f.assert_called_once_with(self, APIModelMock(), 11, (), {})

    @mock.patch.object(pecan, 'response', mock.MagicMock(status=200))
    def test_expose_schema_validation_failed(self):

        @base.jsexpose(body_cls=FakeModel)
        def f(self, body, *args, **kwargs):
            self.f(self, body, *args, **kwargs)

        pecan.request.json = {'a': '123'}
        rtn_val = f(self)
        self.assertEqual(rtn_val, 'null')
        pecan.request.json = {'a': '123', 'b': '456'}
        self.assertRaisesRegexp(exc.HTTPBadRequest, ''b' was unexpected', f, self)
