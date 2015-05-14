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

import mongoengine as me

from st2common import log as logging
from st2common.constants import pack as pack_constants
from st2common.models.db import stormbase
from st2common.models.system import common as common_models


__all__ = ['PolicyTypeReference',
           'PolicyTypeDB',
           'PolicyDB']

LOG = logging.getLogger(__name__)


class PolicyTypeReference(object):
    """
    Class used for referring to policy types which belong to a resource type.
    """
    separator = '.'

    def __init__(self, resource_type=None, name=None):
        self.resource_type = self.validate_resource_type(resource_type)
        self.name = name
        self.ref = self.to_string_reference(resource_type=resource_type, name=name)

    @classmethod
    def is_reference(cls, ref):
        """
        This method uses a very naive approach to determine if the provided
        string is a reference - it only checks if this string contains
        a separator.

        :rtype ref: ``str``
        """
        return ref and cls.separator in ref and ref.index(cls.separator) > 0

    @classmethod
    def from_string_reference(cls, ref):
        return cls(resource_type=cls.get_resource_type(ref),
                   name=cls.get_name(ref))

    @classmethod
    def to_string_reference(cls, resource_type=None, name=None):
        if not resource_type or not name:
            raise ValueError('Both resource_type and name are required for building ref. '
                             'resource_type=%s, name=%s' % (resource_type, name))

        resource_type = cls.validate_resource_type(resource_type)
        return cls.separator.join([resource_type, name])

    @classmethod
    def validate_resource_type(cls, resource_type):
        if not resource_type:
            raise ValueError('Resource type should not be empty.')

        if cls.separator in resource_type:
            raise ValueError('Resource type should not contain "%s".' % cls.separator)

        return resource_type

    @classmethod
    def get_resource_type(cls, ref):
        try:
            if not cls.is_reference(ref):
                raise ValueError('%s is not a valid reference.' % ref)

            return ref.split(cls.separator, 1)[0]
        except (ValueError, IndexError, AttributeError):
            raise common_models.InvalidReferenceError(ref=ref)

    @classmethod
    def get_name(cls, ref):
        try:
            if not cls.is_reference(ref):
                raise ValueError('%s is not a valid reference.' % ref)

            return ref.split(cls.separator, 1)[1]
        except (ValueError, IndexError, AttributeError):
            raise common_models.InvalidReferenceError(ref=ref)

    def __repr__(self):
        return ('<%s resource_type=%s,name=%s,ref=%s>' %
                (self.__class__.__name__, self.resource_type, self.name, self.ref))


class PolicyTypeDB(stormbase.StormBaseDB):
    """
    The representation of an PolicyType in the system.

    Attributes:
        id: See StormBaseAPI
        name: See StormBaseAPI
        description: See StormBaseAPI
        resource_type: The type of resource that this policy type can be applied to.
        enabled: A flag indicating whether the policies for this type is enabled.
        module: The python module that implements the policy for this type.
        parameters: The specification for parameters for the policy type.
    """
    ref = me.StringField(required=True)
    resource_type = me.StringField(
        required=True,
        unique_with='name',
        help_text='The type of resource that this policy type can be applied to.')
    enabled = me.BooleanField(
        required=True,
        default=True,
        help_text='A flag indicating whether the runner for this type is enabled.')
    module = me.StringField(
        required=True,
        help_text='The python module that implements the policy for this type.')
    parameters = me.DictField(
        help_text='The specification for parameters for the policy type.')

    def __init__(self, *args, **kwargs):
        super(PolicyTypeDB, self).__init__(*args, **kwargs)
        self.ref = PolicyTypeReference.to_string_reference(resource_type=self.resource_type,
                                                           name=self.name)

    def get_reference(self):
        """
        Retrieve reference object for this model.

        :rtype: :class:`PolicyReference`
        """
        return PolicyTypeReference(resource_type=self.resource_type, name=self.name)


class PolicyDB(stormbase.StormFoundationDB, stormbase.ContentPackResourceMixin):
    """
    The representation for a policy in the system.

    Attribute:
        enabled: A flag indicating whether this policy is enabled in the system.
        resource_ref: The resource that this policy is applied to.
        policy_type: The type of policy.
        parameters: The specification of input parameters for the policy.
    """
    name = me.StringField(required=True)
    ref = me.StringField(required=True)
    pack = me.StringField(
        required=False,
        default=pack_constants.DEFAULT_PACK_NAME,
        unique_with='name',
        help_text='Name of the content pack.')
    description = me.StringField()
    enabled = me.BooleanField(
        required=True,
        default=True,
        help_text='A flag indicating whether this policy is enabled in the system.')
    resource_ref = me.StringField(
        required=True,
        help_text='The resource that this policy is applied to.')
    policy_type = me.StringField(
        required=True,
        unique_with='resource_ref',
        help_text='The type of policy.')
    parameters = me.DictField(
        help_text='The specification of input parameters for the policy.')

    def __init__(self, *args, **kwargs):
        super(PolicyDB, self).__init__(*args, **kwargs)
        self.ref = common_models.ResourceReference.to_string_reference(pack=self.pack,
                                                                       name=self.name)


MODELS = [PolicyTypeDB, PolicyDB]
