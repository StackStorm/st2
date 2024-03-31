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

"""
Plugin which tells Pylint how to handle mongoengine document classes.
"""
# pylint: disable=E1120,E1125

import astroid

from astroid import MANAGER
from astroid import nodes

# A list of class names for which we want to skip the checks
CLASS_NAME_BLACKLIST = []


def register(linter):
    pass


def transform(cls):
    if cls.name in CLASS_NAME_BLACKLIST:
        return

    if cls.name == "StormFoundationDB":
        # _fields get added automagically by mongoengine
        if "_fields" not in cls.locals:
            cls.locals["_fields"] = [
                nodes.Dict(
                    cls.lineno,
                    cls.col_offset,
                    parent=cls,
                    end_lineno=cls.end_lineno,
                    end_col_offset=cls.end_col_offset,
                )
            ]

    if cls.name.endswith("DB"):
        # mongoengine explicitly declared "id" field on each class so we teach pylint about that
        property_name = "id"
        node = astroid.ClassDef(
            property_name,
            cls.lineno,
            cls.col_offset,
            parent=cls,
            end_lineno=cls.end_lineno,
            end_col_offset=cls.end_col_offset,
        )
        cls.locals[property_name] = [node]


MANAGER.register_transform(astroid.ClassDef, transform)
