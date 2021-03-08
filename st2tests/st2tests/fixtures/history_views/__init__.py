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
import os
import yaml
import glob
import six


PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)))
FILES = glob.glob("%s/*.yaml" % PATH)
ARTIFACTS = {}


for f in FILES:
    f_name = os.path.split(f)[1]
    name = six.text_type(os.path.splitext(f_name)[0])
    with open(f, "r") as fd:
        ARTIFACTS[name] = yaml.safe_load(fd)
