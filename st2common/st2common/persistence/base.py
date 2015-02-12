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

from mongoengine import NotUniqueError
from st2common.exceptions.db import StackStormDBObjectConflictError
from st2common.models.system.common import ResourceReference

import abc
import six

from st2common import log as logging


LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class Access(object):

    @classmethod
    @abc.abstractmethod
    def _get_impl(cls):
        pass

    @classmethod
    @abc.abstractmethod
    def _get_publisher(cls):
        return None

    @classmethod
    @abc.abstractmethod
    def _get_by_object(cls, object):
        return None

    @classmethod
    def get_by_name(cls, value):
        return cls._get_impl().get_by_name(value)

    @classmethod
    def get_by_id(cls, value):
        return cls._get_impl().get_by_id(value)

    @classmethod
    def get(cls, *args, **kwargs):
        return cls._get_impl().get(*args, **kwargs)

    @classmethod
    def get_all(cls, *args, **kwargs):
        return cls._get_impl().get_all(*args, **kwargs)

    @classmethod
    def count(cls, *args, **kwargs):
        return cls._get_impl().count(*args, **kwargs)

    @classmethod
    def query(cls, *args, **kwargs):
        return cls._get_impl().query(*args, **kwargs)

    @classmethod
    def distinct(cls, *args, **kwargs):
        return cls._get_impl().distinct(*args, **kwargs)

    @classmethod
    def aggregate(cls, *args, **kwargs):
        return cls._get_impl().aggregate(*args, **kwargs)

    @classmethod
    def add_or_update(cls, model_object, publish=True):
        pre_persist_id = model_object.id
        try:
            model_object = cls._get_impl().add_or_update(model_object)
        except NotUniqueError as e:
            LOG.exception('Conflict while trying to save in DB.')
            # On a conflict determine the conflicting object and return its id in
            # the raised exception.
            conflict_object = cls._get_by_object(model_object)
            conflict_id = str(conflict_object.id) if conflict_object else None
            raise StackStormDBObjectConflictError(str(e), conflict_id)
        publisher = cls._get_publisher()
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
    def delete(cls, model_object, publish=True):
        persisted_object = cls._get_impl().delete(model_object)
        publisher = cls._get_publisher()
        if publisher and publish:
            # using model_object.
            publisher.publish_delete(model_object)
        return persisted_object


class ContentPackResource(Access):

    @classmethod
    def get_by_ref(cls, ref):
        if not ref:
            return None

        ref_obj = ResourceReference.from_string_reference(ref=ref)
        result = cls.query(name=ref_obj.name,
                           pack=ref_obj.pack).first()
        return result

    @classmethod
    def _get_by_object(cls, object):
        # For an object with a resourcepack pack.name is unique.
        name = getattr(object, 'name', '')
        pack = getattr(object, 'pack', '')
        return cls.get_by_ref(ResourceReference.to_string_reference(pack=pack, name=name))
