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

from st2common.models.system.common import ResourceReference


import abc
import six

from st2common import log as logging


LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class Access(object):

    @classmethod
    @abc.abstractmethod
    def _get_impl(kls):
        pass

    @classmethod
    @abc.abstractmethod
    def _get_publisher(kls):
        return None

    @classmethod
    def get_by_name(kls, value):
        return kls._get_impl().get_by_name(value)

    @classmethod
    def get_by_id(kls, value):
        return kls._get_impl().get_by_id(value)

    @classmethod
    def get(kls, *args, **kwargs):
        return kls._get_impl().get(*args, **kwargs)

    @classmethod
    def get_all(kls, *args, **kwargs):
        return kls._get_impl().get_all(*args, **kwargs)

    @classmethod
    def count(kls, *args, **kwargs):
        return kls._get_impl().count(*args, **kwargs)

    @classmethod
    def query(kls, *args, **kwargs):
        return kls._get_impl().query(*args, **kwargs)

    @classmethod
    def distinct(kls, *args, **kwargs):
        return kls._get_impl().distinct(*args, **kwargs)

    @classmethod
    def aggregate(kls, *args, **kwargs):
        return kls._get_impl().aggregate(*args, **kwargs)

    @classmethod
    def add_or_update(kls, model_object, publish=True):
        pre_persist_id = model_object.id
        model_object = kls._get_impl().add_or_update(model_object)
        publisher = kls._get_publisher()
        try:
            if publisher and publish:
                if str(pre_persist_id) == str(model_object.id):
                    publisher.publish_update(model_object)
                else:
                    publisher.publish_create(model_object)
        except:
            LOG.exception('publish failed.')
        return model_object

    @classmethod
    def delete(kls, model_object, publish=True):
        persisted_object = kls._get_impl().delete(model_object)
        publisher = kls._get_publisher()
        if publisher and publish:
            # using model_object.
            publisher.publish_delete(model_object)
        return persisted_object


class ContentPackResourceMixin():
    @classmethod
    def get_by_ref(cls, ref):
        if not ref:
            return None

        ref_obj = ResourceReference.from_string_reference(ref=ref)
        result = cls.query(name=ref_obj.name,
                           pack=ref_obj.pack).first()
        return result
