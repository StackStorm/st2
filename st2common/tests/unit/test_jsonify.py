import unittest2

import st2common.util.jsonify as jsonify


class JsonifyTests(unittest2.TestCase):

    def test_none_object(self):
        obj = None
        self.assertTrue(jsonify.json_loads(obj) is None)

    def test_no_keys(self):
        obj = {'foo': '{"bar": "baz"}'}
        transformed_obj = jsonify.json_loads(obj)
        self.assertTrue(transformed_obj['foo']['bar'] == 'baz')

    def test_no_json_value(self):
        obj = {'foo': 'bar'}
        transformed_obj = jsonify.json_loads(obj)
        self.assertTrue(transformed_obj['foo'] == 'bar')

    def test_happy_case(self):
        obj = {'foo': '{"bar": "baz"}', 'yo': 'bibimbao'}
        transformed_obj = jsonify.json_loads(obj, ['yo'])
        self.assertTrue(transformed_obj['yo'] == 'bibimbao')
