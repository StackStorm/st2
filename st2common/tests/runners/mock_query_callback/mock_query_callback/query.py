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

from st2common.query.base import Querier
from st2common.constants import action as action_constants


def get_instance():
    return MockQueryCallbackQuerier()


class MockQueryCallbackQuerier(Querier):

    def __init__(self, *args, **kwargs):
        super(MockQueryCallbackQuerier, self).__init__(*args, **kwargs)

    def query(self, execution_id, query_context, last_query_time=None):
        return (action_constants.LIVEACTION_STATUS_SUCCEEDED, {'called_with': {execution_id: query_context}})
