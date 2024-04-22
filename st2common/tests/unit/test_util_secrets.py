# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
import unittest

from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE
from st2common.util import secrets

################################################################################

TEST_FLAT_SCHEMA = {
    "arg_required_no_default": {
        "description": "Foo",
        "required": True,
        "type": "string",
        "secret": False,
    },
    "arg_optional_no_type_secret": {"description": "Bar", "secret": True},
    "arg_optional_type_array": {"description": "Who" "s the fairest?", "type": "array"},
    "arg_optional_type_object": {
        "description": "Who" "s the fairest of them?",
        "type": "object",
    },
}

TEST_FLAT_SECRET_PARAMS = {"arg_optional_no_type_secret": None}

################################################################################

TEST_NO_SECRETS_SCHEMA = {
    "arg_required_no_default": {
        "description": "Foo",
        "required": True,
        "type": "string",
        "secret": False,
    }
}

TEST_NO_SECRETS_SECRET_PARAMS = {}

################################################################################

TEST_NESTED_OBJECTS_SCHEMA = {
    "arg_string": {
        "description": "Junk",
        "type": "string",
    },
    "arg_optional_object": {
        "description": "Mirror",
        "type": "object",
        "properties": {
            "arg_nested_object": {
                "description": "Mirror mirror",
                "type": "object",
                "properties": {
                    "arg_double_nested_secret": {
                        "description": "Deep, deep down",
                        "type": "string",
                        "secret": True,
                    }
                },
            },
            "arg_nested_secret": {
                "description": "Deep down",
                "type": "string",
                "secret": True,
            },
        },
    },
}

TEST_NESTED_OBJECTS_SECRET_PARAMS = {
    "arg_optional_object": {
        "arg_nested_secret": "string",
        "arg_nested_object": {
            "arg_double_nested_secret": "string",
        },
    }
}

################################################################################

TEST_ARRAY_SCHEMA = {
    "arg_optional_array": {
        "description": "Mirror",
        "type": "array",
        "items": {"description": "down", "type": "string", "secret": True},
    }
}

TEST_ARRAY_SECRET_PARAMS = {"arg_optional_array": ["string"]}


################################################################################

TEST_ROOT_ARRAY_SCHEMA = {
    "description": "Mirror",
    "type": "array",
    "items": {
        "description": "down",
        "type": "object",
        "properties": {"secret_field_in_object": {"type": "string", "secret": True}},
    },
}

TEST_ROOT_ARRAY_SECRET_PARAMS = [{"secret_field_in_object": "string"}]

################################################################################

TEST_ROOT_OBJECT_SCHEMA = {
    "description": "root",
    "type": "object",
    "properties": {
        "arg_level_one": {
            "description": "down",
            "type": "object",
            "properties": {
                "secret_field_in_object": {"type": "string", "secret": True}
            },
        }
    },
}

TEST_ROOT_OBJECT_SECRET_PARAMS = {"arg_level_one": {"secret_field_in_object": "string"}}

################################################################################

TEST_NESTED_ARRAYS_SCHEMA = {
    "arg_optional_array": {
        "description": "Mirror",
        "type": "array",
        "items": {"description": "Deep down", "type": "string", "secret": True},
    },
    "arg_optional_double_array": {
        "description": "Mirror",
        "type": "array",
        "items": {
            "type": "array",
            "items": {"description": "Deep down", "type": "string", "secret": True},
        },
    },
    "arg_optional_tripple_array": {
        "description": "Mirror",
        "type": "array",
        "items": {
            "type": "array",
            "items": {
                "type": "array",
                "items": {"description": "Deep down", "type": "string", "secret": True},
            },
        },
    },
    "arg_optional_quad_array": {
        "description": "Mirror",
        "type": "array",
        "items": {
            "type": "array",
            "items": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {
                        "description": "Deep down",
                        "type": "string",
                        "secret": True,
                    },
                },
            },
        },
    },
}

TEST_NESTED_ARRAYS_SECRET_PARAMS = {
    "arg_optional_array": ["string"],
    "arg_optional_double_array": [["string"]],
    "arg_optional_tripple_array": [[["string"]]],
    "arg_optional_quad_array": [[[["string"]]]],
}

################################################################################

TEST_NESTED_OBJECT_WITH_ARRAY_SCHEMA = {
    "arg_optional_object_with_array": {
        "description": "Mirror",
        "type": "object",
        "properties": {
            "arg_nested_array": {
                "description": "Mirror",
                "type": "array",
                "items": {"description": "Deep down", "type": "string", "secret": True},
            }
        },
    }
}

TEST_NESTED_OBJECT_WITH_ARRAY_SECRET_PARAMS = {
    "arg_optional_object_with_array": {"arg_nested_array": ["string"]}
}

################################################################################

TEST_NESTED_OBJECT_WITH_DOUBLE_ARRAY_SCHEMA = {
    "arg_optional_object_with_double_array": {
        "description": "Mirror",
        "type": "object",
        "properties": {
            "arg_double_nested_array": {
                "description": "Mirror",
                "type": "array",
                "items": {
                    "description": "Mirror",
                    "type": "array",
                    "items": {
                        "description": "Deep down",
                        "type": "string",
                        "secret": True,
                    },
                },
            }
        },
    }
}

TEST_NESTED_OBJECT_WITH_DOUBLE_ARRAY_SECRET_PARAMS = {
    "arg_optional_object_with_double_array": {"arg_double_nested_array": [["string"]]}
}

################################################################################

TEST_NESTED_ARRAY_WITH_OBJECT_SCHEMA = {
    "arg_optional_array_with_object": {
        "description": "Mirror",
        "type": "array",
        "items": {
            "description": "Mirror",
            "type": "object",
            "properties": {
                "arg_nested_secret": {
                    "description": "Deep down",
                    "type": "string",
                    "secret": True,
                }
            },
        },
    }
}

TEST_NESTED_ARRAY_WITH_OBJECT_SECRET_PARAMS = {
    "arg_optional_array_with_object": [{"arg_nested_secret": "string"}]
}

################################################################################

TEST_SECRET_ARRAY_SCHEMA = {
    "arg_secret_array": {
        "description": "Mirror",
        "type": "array",
        "secret": True,
    }
}

TEST_SECRET_ARRAY_SECRET_PARAMS = {"arg_secret_array": "array"}

################################################################################

TEST_SECRET_OBJECT_SCHEMA = {
    "arg_secret_object": {
        "type": "object",
        "secret": True,
    }
}

TEST_SECRET_OBJECT_SECRET_PARAMS = {"arg_secret_object": "object"}


################################################################################

TEST_SECRET_ROOT_ARRAY_SCHEMA = {
    "description": "secret array",
    "type": "array",
    "secret": True,
    "items": {
        "description": "down",
        "type": "object",
        "properties": {"secret_field_in_object": {"type": "string", "secret": True}},
    },
}

TEST_SECRET_ROOT_ARRAY_SECRET_PARAMS = "array"

################################################################################

TEST_SECRET_ROOT_OBJECT_SCHEMA = {
    "description": "secret object",
    "type": "object",
    "secret": True,
    "proeprteis": {
        "arg_level_one": {
            "description": "down",
            "type": "object",
            "properties": {
                "secret_field_in_object": {"type": "string", "secret": True}
            },
        }
    },
}

TEST_SECRET_ROOT_OBJECT_SECRET_PARAMS = "object"

################################################################################

TEST_SECRET_NESTED_OBJECTS_SCHEMA = {
    "arg_object": {
        "description": "Mirror",
        "type": "object",
        "properties": {
            "arg_nested_object": {
                "description": "Mirror mirror",
                "type": "object",
                "secret": True,
                "properties": {
                    "arg_double_nested_secret": {
                        "description": "Deep, deep down",
                        "type": "string",
                        "secret": True,
                    }
                },
            },
            "arg_nested_secret": {
                "description": "Deep down",
                "type": "string",
                "secret": True,
            },
        },
    },
    "arg_secret_object": {
        "description": "Mirror",
        "type": "object",
        "secret": True,
        "properties": {
            "arg_nested_object": {
                "description": "Mirror mirror",
                "type": "object",
                "secret": True,
                "properties": {
                    "arg_double_nested_secret": {
                        "description": "Deep, deep down",
                        "type": "string",
                        "secret": True,
                    }
                },
            },
            "arg_nested_secret": {
                "description": "Deep down",
                "type": "string",
                "secret": True,
            },
        },
    },
}

TEST_SECRET_NESTED_OBJECTS_SECRET_PARAMS = {
    "arg_object": {"arg_nested_secret": "string", "arg_nested_object": "object"},
    "arg_secret_object": "object",
}


################################################################################

TEST_SECRET_NESTED_ARRAYS_SCHEMA = {
    "arg_optional_array": {
        "description": "Mirror",
        "type": "array",
        "secret": True,
        "items": {"description": "Deep down", "type": "string"},
    },
    "arg_optional_double_array": {
        "description": "Mirror",
        "type": "array",
        "secret": True,
        "items": {
            "type": "array",
            "items": {
                "description": "Deep down",
                "type": "string",
            },
        },
    },
    "arg_optional_tripple_array": {
        "description": "Mirror",
        "type": "array",
        "items": {
            "type": "array",
            "secret": True,
            "items": {
                "type": "array",
                "items": {
                    "description": "Deep down",
                    "type": "string",
                },
            },
        },
    },
    "arg_optional_quad_array": {
        "description": "Mirror",
        "type": "array",
        "items": {
            "type": "array",
            "items": {
                "type": "array",
                "secret": True,
                "items": {
                    "type": "array",
                    "items": {
                        "description": "Deep down",
                        "type": "string",
                    },
                },
            },
        },
    },
}

TEST_SECRET_NESTED_ARRAYS_SECRET_PARAMS = {
    "arg_optional_array": "array",
    "arg_optional_double_array": "array",
    "arg_optional_tripple_array": ["array"],
    "arg_optional_quad_array": [["array"]],
}

################################################################################


class SecretUtilsTestCase(unittest.TestCase):
    def test_get_secret_parameters_flat(self):
        result = secrets.get_secret_parameters(TEST_FLAT_SCHEMA)
        self.assertEqual(TEST_FLAT_SECRET_PARAMS, result)

    def test_get_secret_parameters_no_secrets(self):
        result = secrets.get_secret_parameters(TEST_NO_SECRETS_SCHEMA)
        self.assertEqual(TEST_NO_SECRETS_SECRET_PARAMS, result)

    def test_get_secret_parameters_nested_objects(self):
        result = secrets.get_secret_parameters(TEST_NESTED_OBJECTS_SCHEMA)
        self.assertEqual(TEST_NESTED_OBJECTS_SECRET_PARAMS, result)

    def test_get_secret_parameters_array(self):
        result = secrets.get_secret_parameters(TEST_ARRAY_SCHEMA)
        self.assertEqual(TEST_ARRAY_SECRET_PARAMS, result)

    def test_get_secret_parameters_root_array(self):
        result = secrets.get_secret_parameters(TEST_ROOT_ARRAY_SCHEMA)
        self.assertEqual(TEST_ROOT_ARRAY_SECRET_PARAMS, result)

    def test_get_secret_parameters_root_object(self):
        result = secrets.get_secret_parameters(TEST_ROOT_OBJECT_SCHEMA)
        self.assertEqual(TEST_ROOT_OBJECT_SECRET_PARAMS, result)

    def test_get_secret_parameters_nested_arrays(self):
        result = secrets.get_secret_parameters(TEST_NESTED_ARRAYS_SCHEMA)
        self.assertEqual(TEST_NESTED_ARRAYS_SECRET_PARAMS, result)

    def test_get_secret_parameters_nested_object_with_array(self):
        result = secrets.get_secret_parameters(TEST_NESTED_OBJECT_WITH_ARRAY_SCHEMA)
        self.assertEqual(TEST_NESTED_OBJECT_WITH_ARRAY_SECRET_PARAMS, result)

    def test_get_secret_parameters_nested_object_with_double_array(self):
        result = secrets.get_secret_parameters(
            TEST_NESTED_OBJECT_WITH_DOUBLE_ARRAY_SCHEMA
        )
        self.assertEqual(TEST_NESTED_OBJECT_WITH_DOUBLE_ARRAY_SECRET_PARAMS, result)

    def test_get_secret_parameters_nested_array_with_object(self):
        result = secrets.get_secret_parameters(TEST_NESTED_ARRAY_WITH_OBJECT_SCHEMA)
        self.assertEqual(TEST_NESTED_ARRAY_WITH_OBJECT_SECRET_PARAMS, result)

    def test_get_secret_parameters_secret_array(self):
        result = secrets.get_secret_parameters(TEST_SECRET_ARRAY_SCHEMA)
        self.assertEqual(TEST_SECRET_ARRAY_SECRET_PARAMS, result)

    def test_get_secret_parameters_secret_object(self):
        result = secrets.get_secret_parameters(TEST_SECRET_OBJECT_SCHEMA)
        self.assertEqual(TEST_SECRET_OBJECT_SECRET_PARAMS, result)

    def test_get_secret_parameters_secret_root_array(self):
        result = secrets.get_secret_parameters(TEST_SECRET_ROOT_ARRAY_SCHEMA)
        self.assertEqual(TEST_SECRET_ROOT_ARRAY_SECRET_PARAMS, result)

    def test_get_secret_parameters_secret_root_object(self):
        result = secrets.get_secret_parameters(TEST_SECRET_ROOT_OBJECT_SCHEMA)
        self.assertEqual(TEST_SECRET_ROOT_OBJECT_SECRET_PARAMS, result)

    def test_get_secret_parameters_secret_nested_arrays(self):
        result = secrets.get_secret_parameters(TEST_SECRET_NESTED_ARRAYS_SCHEMA)
        self.assertEqual(TEST_SECRET_NESTED_ARRAYS_SECRET_PARAMS, result)

    def test_get_secret_parameters_secret_nested_objects(self):
        result = secrets.get_secret_parameters(TEST_SECRET_NESTED_OBJECTS_SCHEMA)
        self.assertEqual(TEST_SECRET_NESTED_OBJECTS_SECRET_PARAMS, result)

    ############################################################################

    def test_mask_secret_parameters_flat(self):
        parameters = {
            "arg_required_no_default": "test",
            "arg_optional_no_type_secret": None,
        }
        result = secrets.mask_secret_parameters(parameters, TEST_FLAT_SECRET_PARAMS)
        expected = {
            "arg_required_no_default": "test",
            "arg_optional_no_type_secret": MASKED_ATTRIBUTE_VALUE,
        }
        self.assertEqual(expected, result)

    def test_mask_secret_parameters_no_secrets(self):
        parameters = {"arg_required_no_default": "junk"}
        result = secrets.mask_secret_parameters(
            parameters, TEST_NO_SECRETS_SECRET_PARAMS
        )
        expected = {"arg_required_no_default": "junk"}
        self.assertEqual(expected, result)

    def test_mask_secret_parameters_nested_objects(self):
        parameters = {
            "arg_optional_object": {
                "arg_nested_secret": "nested Secret",
                "arg_nested_object": {
                    "arg_double_nested_secret": "double nested $ecret",
                },
            }
        }
        result = secrets.mask_secret_parameters(
            parameters, TEST_NESTED_OBJECTS_SECRET_PARAMS
        )
        expected = {
            "arg_optional_object": {
                "arg_nested_secret": MASKED_ATTRIBUTE_VALUE,
                "arg_nested_object": {
                    "arg_double_nested_secret": MASKED_ATTRIBUTE_VALUE,
                },
            }
        }
        self.assertEqual(expected, result)

    def test_mask_secret_parameters_array(self):
        parameters = {
            "arg_optional_array": [
                "$ecret $tring 1",
                "$ecret $tring 2",
                "$ecret $tring 3",
            ]
        }
        result = secrets.mask_secret_parameters(parameters, TEST_ARRAY_SECRET_PARAMS)
        expected = {
            "arg_optional_array": [
                MASKED_ATTRIBUTE_VALUE,
                MASKED_ATTRIBUTE_VALUE,
                MASKED_ATTRIBUTE_VALUE,
            ]
        }
        self.assertEqual(expected, result)

    def test_mask_secret_parameters_root_array(self):
        parameters = [
            {"secret_field_in_object": "Secret $tr!ng"},
            {"secret_field_in_object": "Secret $tr!ng 2"},
            {"secret_field_in_object": "Secret $tr!ng 3"},
            {"secret_field_in_object": "Secret $tr!ng 4"},
        ]

        result = secrets.mask_secret_parameters(
            parameters, TEST_ROOT_ARRAY_SECRET_PARAMS
        )
        expected = [
            {"secret_field_in_object": MASKED_ATTRIBUTE_VALUE},
            {"secret_field_in_object": MASKED_ATTRIBUTE_VALUE},
            {"secret_field_in_object": MASKED_ATTRIBUTE_VALUE},
            {"secret_field_in_object": MASKED_ATTRIBUTE_VALUE},
        ]
        self.assertEqual(expected, result)

    def test_mask_secret_parameters_root_object(self):
        parameters = {"arg_level_one": {"secret_field_in_object": "Secret $tr!ng"}}

        result = secrets.mask_secret_parameters(
            parameters, TEST_ROOT_OBJECT_SECRET_PARAMS
        )
        expected = {"arg_level_one": {"secret_field_in_object": MASKED_ATTRIBUTE_VALUE}}
        self.assertEqual(expected, result)

    def test_mask_secret_parameters_nested_arrays(self):
        parameters = {
            "arg_optional_array": [
                "secret 1",
                "secret 2",
                "secret 3",
            ],
            "arg_optional_double_array": [
                [
                    "secret 4",
                    "secret 5",
                    "secret 6",
                ],
                [
                    "secret 7",
                    "secret 8",
                    "secret 9",
                ],
            ],
            "arg_optional_tripple_array": [
                [["secret 10", "secret 11"], ["secret 12", "secret 13", "secret 14"]],
                [["secret 15", "secret 16"]],
            ],
            "arg_optional_quad_array": [[[["secret 17", "secret 18"], ["secret 19"]]]],
        }

        result = secrets.mask_secret_parameters(
            parameters, TEST_NESTED_ARRAYS_SECRET_PARAMS
        )
        expected = {
            "arg_optional_array": [
                MASKED_ATTRIBUTE_VALUE,
                MASKED_ATTRIBUTE_VALUE,
                MASKED_ATTRIBUTE_VALUE,
            ],
            "arg_optional_double_array": [
                [
                    MASKED_ATTRIBUTE_VALUE,
                    MASKED_ATTRIBUTE_VALUE,
                    MASKED_ATTRIBUTE_VALUE,
                ],
                [
                    MASKED_ATTRIBUTE_VALUE,
                    MASKED_ATTRIBUTE_VALUE,
                    MASKED_ATTRIBUTE_VALUE,
                ],
            ],
            "arg_optional_tripple_array": [
                [
                    [MASKED_ATTRIBUTE_VALUE, MASKED_ATTRIBUTE_VALUE],
                    [
                        MASKED_ATTRIBUTE_VALUE,
                        MASKED_ATTRIBUTE_VALUE,
                        MASKED_ATTRIBUTE_VALUE,
                    ],
                ],
                [[MASKED_ATTRIBUTE_VALUE, MASKED_ATTRIBUTE_VALUE]],
            ],
            "arg_optional_quad_array": [
                [
                    [
                        [MASKED_ATTRIBUTE_VALUE, MASKED_ATTRIBUTE_VALUE],
                        [MASKED_ATTRIBUTE_VALUE],
                    ]
                ]
            ],
        }
        self.assertEqual(expected, result)

    def test_mask_secret_parameters_nested_object_with_array(self):
        parameters = {
            "arg_optional_object_with_array": {
                "arg_nested_array": [
                    "secret array value 1",
                    "secret array value 2",
                    "secret array value 3",
                ]
            }
        }
        result = secrets.mask_secret_parameters(
            parameters, TEST_NESTED_OBJECT_WITH_ARRAY_SECRET_PARAMS
        )
        expected = {
            "arg_optional_object_with_array": {
                "arg_nested_array": [
                    MASKED_ATTRIBUTE_VALUE,
                    MASKED_ATTRIBUTE_VALUE,
                    MASKED_ATTRIBUTE_VALUE,
                ]
            }
        }
        self.assertEqual(expected, result)

    def test_mask_secret_parameters_nested_object_with_double_array(self):
        parameters = {
            "arg_optional_object_with_double_array": {
                "arg_double_nested_array": [
                    ["secret 1", "secret 2", "secret 3"],
                    [
                        "secret 4",
                        "secret 5",
                        "secret 6",
                    ],
                    [
                        "secret 7",
                        "secret 8",
                        "secret 9",
                        "secret 10",
                    ],
                ]
            }
        }
        result = secrets.mask_secret_parameters(
            parameters, TEST_NESTED_OBJECT_WITH_DOUBLE_ARRAY_SECRET_PARAMS
        )
        expected = {
            "arg_optional_object_with_double_array": {
                "arg_double_nested_array": [
                    [
                        MASKED_ATTRIBUTE_VALUE,
                        MASKED_ATTRIBUTE_VALUE,
                        MASKED_ATTRIBUTE_VALUE,
                    ],
                    [
                        MASKED_ATTRIBUTE_VALUE,
                        MASKED_ATTRIBUTE_VALUE,
                        MASKED_ATTRIBUTE_VALUE,
                    ],
                    [
                        MASKED_ATTRIBUTE_VALUE,
                        MASKED_ATTRIBUTE_VALUE,
                        MASKED_ATTRIBUTE_VALUE,
                        MASKED_ATTRIBUTE_VALUE,
                    ],
                ]
            }
        }
        self.assertEqual(expected, result)

    def test_mask_secret_parameters_nested_array_with_object(self):
        parameters = {
            "arg_optional_array_with_object": [
                {"arg_nested_secret": "secret 1"},
                {"arg_nested_secret": "secret 2"},
                {"arg_nested_secret": "secret 3"},
            ]
        }
        result = secrets.mask_secret_parameters(
            parameters, TEST_NESTED_ARRAY_WITH_OBJECT_SECRET_PARAMS
        )
        expected = {
            "arg_optional_array_with_object": [
                {"arg_nested_secret": MASKED_ATTRIBUTE_VALUE},
                {"arg_nested_secret": MASKED_ATTRIBUTE_VALUE},
                {"arg_nested_secret": MASKED_ATTRIBUTE_VALUE},
            ]
        }
        self.assertEqual(expected, result)

    def test_mask_secret_parameters_secret_array(self):
        parameters = {"arg_secret_array": ["abc", 123, True]}
        result = secrets.mask_secret_parameters(
            parameters, TEST_SECRET_ARRAY_SECRET_PARAMS
        )
        expected = {"arg_secret_array": MASKED_ATTRIBUTE_VALUE}
        self.assertEqual(expected, result)

    def test_mask_secret_parameters_secret_object(self):
        parameters = {
            "arg_secret_object": {
                "abc": 123,
                "key": "value",
                "bool": True,
                "array": ["x", "y", "z"],
                "obj": {"x": "deep"},
            }
        }
        result = secrets.mask_secret_parameters(
            parameters, TEST_SECRET_OBJECT_SECRET_PARAMS
        )
        expected = {"arg_secret_object": MASKED_ATTRIBUTE_VALUE}
        self.assertEqual(expected, result)

    def test_mask_secret_parameters_secret_root_array(self):
        parameters = ["abc", 123, True]
        result = secrets.mask_secret_parameters(
            parameters, TEST_SECRET_ROOT_ARRAY_SECRET_PARAMS
        )
        expected = MASKED_ATTRIBUTE_VALUE
        self.assertEqual(expected, result)

    def test_mask_secret_parameters_secret_root_object(self):
        parameters = {"arg_level_one": {"secret_field_in_object": "Secret $tr!ng"}}
        result = secrets.mask_secret_parameters(
            parameters, TEST_SECRET_ROOT_OBJECT_SECRET_PARAMS
        )
        expected = MASKED_ATTRIBUTE_VALUE
        self.assertEqual(expected, result)

    def test_mask_secret_parameters_secret_nested_arrays(self):
        parameters = {
            "arg_optional_array": [
                "secret 1",
                "secret 2",
                "secret 3",
            ],
            "arg_optional_double_array": [
                [
                    "secret 4",
                    "secret 5",
                    "secret 6",
                ],
                [
                    "secret 7",
                    "secret 8",
                    "secret 9",
                ],
            ],
            "arg_optional_tripple_array": [
                [["secret 10", "secret 11"], ["secret 12", "secret 13", "secret 14"]],
                [["secret 15", "secret 16"]],
            ],
            "arg_optional_quad_array": [[[["secret 17", "secret 18"], ["secret 19"]]]],
        }

        result = secrets.mask_secret_parameters(
            parameters, TEST_SECRET_NESTED_ARRAYS_SECRET_PARAMS
        )

        expected = {
            "arg_optional_array": MASKED_ATTRIBUTE_VALUE,
            "arg_optional_double_array": MASKED_ATTRIBUTE_VALUE,
            "arg_optional_tripple_array": [
                MASKED_ATTRIBUTE_VALUE,
                MASKED_ATTRIBUTE_VALUE,
            ],
            "arg_optional_quad_array": [
                [
                    MASKED_ATTRIBUTE_VALUE,
                ]
            ],
        }
        self.assertEqual(expected, result)

    def test_mask_secret_parameters_secret_nested_objects(self):
        parameters = {
            "arg_object": {
                "arg_nested_secret": "nested Secret",
                "arg_nested_object": {
                    "arg_double_nested_secret": "double nested $ecret",
                },
            },
            "arg_secret_object": {
                "arg_nested_secret": "secret data",
                "arg_nested_object": {
                    "arg_double_nested_secret": "double nested $ecret",
                },
            },
        }
        result = secrets.mask_secret_parameters(
            parameters, TEST_SECRET_NESTED_OBJECTS_SECRET_PARAMS
        )
        expected = {
            "arg_object": {
                "arg_nested_secret": MASKED_ATTRIBUTE_VALUE,
                "arg_nested_object": MASKED_ATTRIBUTE_VALUE,
            },
            "arg_secret_object": MASKED_ATTRIBUTE_VALUE,
        }
        self.assertEqual(expected, result)
