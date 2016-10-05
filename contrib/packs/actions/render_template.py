#!/usr/bin/env python

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

import os

from st2actions.runners.pythonrunner import Action
from st2common.util import jinja as jinja_utils


class RenderTemplateAction(Action):
    def __init__(self, config=None, action_service=None):
        super(RenderTemplateAction, self).__init__(config=config, action_service=action_service)
        self.jinja = jinja_utils.get_jinja_environment(allow_undefined=True)
        self.jinja.tests['in'] = lambda item, list: item in list

    def run(self, template_path, context):
        path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(path, template_path), 'r') as f:
            template = f.read()

        result = self.jinja.from_string(template).render(context)

        return result
