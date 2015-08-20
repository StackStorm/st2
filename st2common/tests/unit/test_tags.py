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

import random
import string

from mongoengine import ValidationError
from st2common.models.db import stormbase
from st2tests import DbTestCase


class TaggedModel(stormbase.StormFoundationDB, stormbase.TagsMixin):
    pass


class TestTags(DbTestCase):

    def test_simple_count(self):
        instance = TaggedModel()
        instance.tags = [stormbase.TagField(name='tag1', value='v1'),
                         stormbase.TagField(name='tag2', value='v2')]
        saved = instance.save()
        retrieved = TaggedModel.objects(id=instance.id).first()
        self.assertEquals(len(saved.tags), len(retrieved.tags), 'Failed to retrieve tags.')

    def test_simple_value(self):
        instance = TaggedModel()
        instance.tags = [stormbase.TagField(name='tag1', value='v1')]
        saved = instance.save()
        retrieved = TaggedModel.objects(id=instance.id).first()
        self.assertEquals(len(saved.tags), len(retrieved.tags), 'Failed to retrieve tags.')
        saved_tag = saved.tags[0]
        retrieved_tag = retrieved.tags[0]
        self.assertEquals(saved_tag.name, retrieved_tag.name, 'Failed to retrieve tag.')
        self.assertEquals(saved_tag.value, retrieved_tag.value, 'Failed to retrieve tag.')

    def test_tag_max_size_restriction(self):
        instance = TaggedModel()
        instance.tags = [stormbase.TagField(name=self._gen_random_string(),
                                            value=self._gen_random_string())]
        saved = instance.save()
        retrieved = TaggedModel.objects(id=instance.id).first()
        self.assertEquals(len(saved.tags), len(retrieved.tags), 'Failed to retrieve tags.')

    def test_name_exceeds_max_size(self):
        instance = TaggedModel()
        instance.tags = [stormbase.TagField(name=self._gen_random_string(1025),
                                            value='v1')]
        try:
            instance.save()
            self.assertTrue(False, 'Expected save to fail')
        except ValidationError:
            pass

    def test_value_exceeds_max_size(self):
        instance = TaggedModel()
        instance.tags = [stormbase.TagField(name='n1',
                                            value=self._gen_random_string(1025))]
        try:
            instance.save()
            self.assertTrue(False, 'Expected save to fail')
        except ValidationError:
            pass

    def _gen_random_string(self, size=1024, chars=string.ascii_lowercase + string.digits):
        return ''.join([random.choice(chars) for _ in range(size)])
