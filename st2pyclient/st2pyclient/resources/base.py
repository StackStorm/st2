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

from abc import ABCMeta

from st2pyclient.exceptions.models import InvalidModelTypeException


class Resource(object):
    __metaclass__ = ABCMeta

    def __init__(self, name, model_class, client=None):
        self.name = name
        self.model_class = model_class
        self.client = client

    def create(self, model_instance):
        if not isinstance(model_instance, self.model_class):
            raise InvalidModelTypeException('Resource %s requires a model type %s.' % (
                                            self.name, self.model_class))
        pass

    def get(self, ref_or_id):
        pass

    def update(self, ref_or_id, model_instance):
        pass

    def delete(self, ref_or_id):
        pass

