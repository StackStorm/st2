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

    def test_try_loads(self):
        # The function json.loads will fail and the function should return the original value.
        values = ['abc', 123, True, object()]
        for value in values:
            self.assertEqual(jsonify.try_loads(value), value)

        # The function json.loads succeed.
        d = '{"a": 1, "b": true}'
        expected = {'a': 1, 'b': True}
        self.assertDictEqual(jsonify.try_loads(d), expected)
