import mock
import pecan
import unittest

from st2common.models import base


@mock.patch.object(pecan, 'request', mock.MagicMock(json={'a': 'b'}))
class TestModelBase(unittest.TestCase):

    def setUp(self):
        super(TestModelBase, self).setUp()
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
        @base.jsexpose(int)
        def f(self, id, *args, **kwargs):
            self.f(self, id, args, kwargs)

        f(self, '11')

        self.f.assert_called_once_with(self, 11, (), {})

    def test_expose_argument_with_default(self):
        @base.jsexpose(int)
        def f(self, id, some=None, *args, **kwargs):
            self.f(self, id, some, args, kwargs)

        f(self, '11')

        self.f.assert_called_once_with(self, 11, None, (), {})

    def test_expose_kv_unused(self):
        @base.jsexpose(int, int, str)
        def f(self, id, *args, **kwargs):
            self.f(self, id, args, kwargs)

        f(self, '11', number='7', name="fox")

        self.f.assert_called_once_with(self, 11, (), {'number': '7', 'name': 'fox'})

    def test_expose_kv_type_casting(self):
        @base.jsexpose(int, int, str)
        def f(self, id, number, name, *args, **kwargs):
            self.f(self, id, number, name, args, kwargs)

        f(self, '11', number='7', name="fox")

        self.f.assert_called_once_with(self, 11, 7, 'fox', (), {})

    def test_expose_body_unused(self):
        APIModelMock = mock.MagicMock()

        @base.jsexpose(body=APIModelMock)
        def f(self, *args, **kwargs):
            self.f(self, args, kwargs)

        f(self)

        APIModelMock.assert_called_once_with(a='b')
        self.f.assert_called_once_with(self, (APIModelMock(),), {})

    def test_expose_body(self):
        APIModelMock = mock.MagicMock()

        @base.jsexpose(body=APIModelMock)
        def f(self, body, *args, **kwargs):
            self.f(self, body, args, kwargs)

        f(self)

        APIModelMock.assert_called_once_with(a='b')
        self.f.assert_called_once_with(self, APIModelMock(), (), {})

    def test_expose_body_and_arguments_unused(self):
        APIModelMock = mock.MagicMock()

        @base.jsexpose(body=APIModelMock)
        def f(self, body, *args, **kwargs):
            self.f(self, body, args, kwargs)

        f(self, '11')

        APIModelMock.assert_called_once_with(a='b')
        self.f.assert_called_once_with(self, APIModelMock(), ('11', ), {})

    def test_expose_body_and_arguments_type_casting(self):
        APIModelMock = mock.MagicMock()

        @base.jsexpose(int, body=APIModelMock)
        def f(self, id, body, *args, **kwargs):
            self.f(self, id, body, args, kwargs)

        f(self, '11')

        APIModelMock.assert_called_once_with(a='b')
        self.f.assert_called_once_with(self, 11, APIModelMock(), (), {})

    @unittest.skip
    def test_expose_body_and_typed_arguments_unused(self):
        APIModelMock = mock.MagicMock()

        @base.jsexpose(int, body=APIModelMock)
        def f(self, id, body, *args, **kwargs):
            self.f(self, id, body, args, kwargs)

        f(self, '11', 'some')

        APIModelMock.assert_called_once_with(a='b')
        self.f.assert_called_once_with(self, 11, APIModelMock(), ('some', ), {})

    @unittest.skip
    def test_expose_body_and_typed_kw_unused(self):
        APIModelMock = mock.MagicMock()

        @base.jsexpose(int, body=APIModelMock)
        def f(self, body, id, *args, **kwargs):
            self.f(self, body, id, args, kwargs)

        f(self, id='11')

        APIModelMock.assert_called_once_with(a='b')
        self.f.assert_called_once_with(self, APIModelMock(), 11, (), {})