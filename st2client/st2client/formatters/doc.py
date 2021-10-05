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

import json
import logging

import orjson
import yaml

from st2client import formatters
from st2client.utils import jsutil

__all__ = ["JsonFormatter", "YAMLFormatter"]

LOG = logging.getLogger(__name__)


class BaseFormatter(formatters.Formatter):
    @classmethod
    def format(self, subject, *args, **kwargs):
        attributes = kwargs.get("attributes", None)
        if type(subject) is str:
            subject = orjson.loads(subject)
        elif not isinstance(subject, (list, tuple)) and not hasattr(
            subject, "__iter__"
        ):
            doc = subject if isinstance(subject, dict) else subject.__dict__
            keys = (
                list(doc.keys())
                if not attributes or "all" in attributes
                else attributes
            )
            docs = jsutil.get_kvps(doc, keys)
        else:
            docs = []
            for item in subject:
                doc = item if isinstance(item, dict) else item.__dict__
                keys = (
                    list(doc.keys())
                    if not attributes or "all" in attributes
                    else attributes
                )
                docs.append(jsutil.get_kvps(doc, keys))

        return docs


class JsonFormatter(BaseFormatter):
    @classmethod
    def format(self, subject, *args, **kwargs):
        docs = BaseFormatter.format(subject, *args, **kwargs)
        return json.dumps(docs, indent=4, sort_keys=True)


class YAMLFormatter(BaseFormatter):
    @classmethod
    def format(self, subject, *args, **kwargs):
        docs = BaseFormatter.format(subject, *args, **kwargs)
        return yaml.safe_dump(docs, indent=4, default_flow_style=False)
