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
import inspect

__all__ = ["Enum"]


class Enum(object):
    @classmethod
    def get_valid_values(cls):
        keys = list(cls.__dict__.keys())
        values = [
            getattr(cls, key)
            for key in keys
            if (not key.startswith("_") and not inspect.ismethod(getattr(cls, key)))
        ]
        return values
