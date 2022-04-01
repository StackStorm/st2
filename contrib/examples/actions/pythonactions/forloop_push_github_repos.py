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

from __future__ import print_function

import six

from st2common.runners.base_action import Action


class PushGithubRepos(Action):
    def run(self, data_to_push):
        try:
            for each_item in data_to_push:
                # Push data to a service here
                print(str(each_item))
        except Exception as e:
            raise Exception("Process failed: {}".format(six.text_type(e)))

        return (True, "Data pushed successfully")
