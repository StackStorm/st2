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

from st2common.models.db.stormbase import TagField

__all__ = [
    'TagsHelper'
]


class TagsHelper(object):

    @staticmethod
    def to_model(tags):
        return [TagField(name=tag.get('name', ''), value=tag.get('value', '')) for tag in tags]

    @staticmethod
    def from_model(tags):
        return [{'name': tag.name, 'value': tag.value} for tag in tags]
