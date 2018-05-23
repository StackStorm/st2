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
import unittest2

from st2common.util import secrets


TEST_SCHEMA_NO_SECRETS = {
    'arg_required_no_default': {
        'description': 'Foo',
        'required': True,
        'type': 'string',
        'secret': False
    }
}

TEST_SCHEMA_FLAT = {
    'arg_required_no_default': {
        'description': 'Foo',
        'required': True,
        'type': 'string',
        'secret': False
    },
    'arg_optional_no_type_secret': {
        'description': 'Bar',
        'secret': True
    },
    'arg_optional_type_array': {
        'description': 'Who''s the fairest?',
        'type': 'array'
    },
    'arg_optional_type_object': {
        'description': 'Who''s the fairest of them?',
        'type': 'object'
    },
}

TEST_SCHEMA_NESTED_OBJECTS = {
    'arg_string': {
        'description': 'Junk',
        'type': 'string',
    },
    'arg_optional_object': {
        'description': 'Mirror',
        'type': 'object',
        'properties': {
            'arg_nested_object': {
                'description': 'Mirror mirror',
                'type': 'object',
                'properties': {
                    'arg_double_nested_secret': {
                        'description': 'Deep, deep down',
                        'type': 'string',
                        'secret': True
                    }
                }
            },
            'arg_nested_secret': {
                'description': 'Deep down',
                'type': 'string',
                'secret': True
            }
        }
    }
}

TEST_SCHEMA_ARRAY = {
    'arg_optional_array': {
        'description': 'Mirror',
        'type': 'array',
        'items': {
            'description': 'down',
            'type': 'string',
            'secret': True
        }
    }
}

TEST_SCHEMA_NESTED_ARRAYS = {
    'arg_optional_array': {
        'description': 'Mirror',
        'type': 'array',
        'items': {
            'description': 'Deep down',
            'type': 'string',
            'secret': True
        }
    },
    'arg_optional_double_array': {
        'description': 'Mirror',
        'type': 'array',
        'items': {
            'type': 'array',
            'items': {
                'description': 'Deep down',
                'type': 'string',
                'secret': True
            }
        }
    },
    'arg_optional_tripple_array': {
        'description': 'Mirror',
        'type': 'array',
        'items': {
            'type': 'array',
            'items': {
                'type': 'array',
                'items': {
                    'description': 'Deep down',
                    'type': 'string',
                    'secret': True
                }
            }
        }
    },
    'arg_optional_quad_array': {
        'description': 'Mirror',
        'type': 'array',
        'items': {
            'type': 'array',
            'items': {
                'type': 'array',
                'items': {
                    'type': 'array',
                    'items': {
                        'description': 'Deep down',
                        'type': 'string',
                        'secret': True
                    }
                }
            }
        }
    }
}

TEST_SCHEMA_NESTED_OBJECT_WITH_ARRAY = {
    'arg_optional_object_with_array': {
        'description': 'Mirror',
        'type': 'object',
        'properties': {
            'arg_nested_array': {
                'description': 'Mirror',
                'type': 'array',
                'items': {
                    'description': 'Deep down',
                    'type': 'string',
                    'secret': True
                }
            }
        }
    }
}

TEST_SCHEMA_NESTED_OBJECT_WITH_DOUBLE_ARRAY = {
    'arg_optional_object_with_double_array': {
        'description': 'Mirror',
        'type': 'object',
        'properties': {
            'arg_double_nested_array': {
                'description': 'Mirror',
                'type': 'array',
                'items': {
                    'description': 'Mirror',
                    'type': 'array',
                    'items': {
                        'description': 'Deep down',
                        'type': 'string',
                        'secret': True
                    }
                }
            }
        }
    }
}

TEST_SCHEMA_NESTED_ARRAY_WITH_OBJECT = {
    'arg_optional_array_with_object': {
        'description': 'Mirror',
        'type': 'array',
        'items': {
            'description': 'Mirror',
            'type': 'object',
            'properties': {
                'arg_nested_secret':  {
                    'description': 'Deep down',
                    'type': 'string',
                    'secret': True
                }
            }
        }
    }
}


class SecretUtilsTestCase(unittest2.TestCase):

    def test_get_secret_parameters_flat(self):
        result = secrets.get_secret_parameters(TEST_SCHEMA_FLAT)
        expected = {'arg_optional_no_type_secret': None}
        self.assertEqual(expected, result)

    def test_get_secret_parameters_no_secrets(self):
        result = secrets.get_secret_parameters(TEST_SCHEMA_NO_SECRETS)
        expected = {}
        self.assertEqual(expected, result)

    def test_get_secret_parameters_nested_objects(self):
        result = secrets.get_secret_parameters(TEST_SCHEMA_NESTED_OBJECTS)
        expected = {
            'arg_optional_object': {
                'arg_nested_secret': 'string',
                'arg_nested_object': {
                    'arg_double_nested_secret': 'string',
                }
            }
        }
        self.assertEqual(expected,  result)

    def test_get_secret_parameters_array(self):
        result = secrets.get_secret_parameters(TEST_SCHEMA_ARRAY)
        expected = {
            'arg_optional_array': [
                'string'
            ]
        }
        self.assertEqual(expected,  result)

    def test_get_secret_parameters_nested_arrays(self):
        result = secrets.get_secret_parameters(TEST_SCHEMA_NESTED_ARRAYS)
        expected = {
            'arg_optional_array': [
                'string'
            ],
            'arg_optional_double_array': [ [
                'string'
            ] ],
            'arg_optional_tripple_array': [ [ [
                'string'
            ] ] ],
            'arg_optional_quad_array': [ [ [ [
                'string'
            ] ] ] ],
        }
        self.assertEqual(expected,  result)

    def test_get_secret_parameters_nested_object_with_array(self):
        result = secrets.get_secret_parameters(TEST_SCHEMA_NESTED_OBJECT_WITH_ARRAY)
        expected = {
            'arg_optional_object_with_array':  {
                'arg_nested_array': [
                    'string'
                ]
            }
        }
        self.assertEqual(expected,  result)

    def test_get_secret_parameters_nested_object_with_double_array(self):
        result = secrets.get_secret_parameters(TEST_SCHEMA_NESTED_OBJECT_WITH_DOUBLE_ARRAY)
        expected = {
            'arg_optional_object_with_double_array':  {
                'arg_double_nested_array': [ [
                    'string'
                ] ]
            }
        }
        self.assertEqual(expected,  result)

    def test_get_secret_parameters_nested_array_with_object(self):
        result = secrets.get_secret_parameters(TEST_SCHEMA_NESTED_ARRAY_WITH_OBJECT)
        expected = {
            'arg_optional_array_with_object': [ {
                'arg_nested_secret': 'string'
            } ]
        }
        self.assertEqual(expected,  result)

    # TODO unit tests for mask_secret_parameters
