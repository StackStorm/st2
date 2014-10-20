from oslo.config import cfg
from tests import FunctionalTest


class TestBase(FunctionalTest):
    def test_defaults(self):
        response = self.app.get('/')
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'],
                         'http://localhost:3000')
        self.assertEqual(response.headers['Access-Control-Allow-Methods'],
                         'GET,POST,PUT,DELETE,OPTIONS')
        self.assertEqual(response.headers['Access-Control-Allow-Headers'],
                         'Content-Type')
        self.assertEqual(response.headers['Access-Control-Expose-Headers'],
                         'Content-Type,X-Limit,X-Total-Count')

    def test_origin(self):
        response = self.app.get('/', headers={
            'origin': 'http://localhost:3000'
        })
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'],
                         'http://localhost:3000')

    def test_additional_origin(self):
        response = self.app.get('/', headers={
            'origin': 'http://dev'
        })
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'],
                         'http://dev')

    def test_wrong_origin(self):
        response = self.app.get('/', headers={
            'origin': 'http://xss'
        })
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'],
                         'null')

    def test_wildcard_origin(self):
        try:
            cfg.CONF.set_override('allow_origin', ['*'], 'api')
            response = self.app.get('/', headers={
                'origin': 'http://xss'
            })
        finally:
            cfg.CONF.clear_override('allow_origin', 'api')
        self.assertEqual(response.status_int, 200)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'],
                         '*')
