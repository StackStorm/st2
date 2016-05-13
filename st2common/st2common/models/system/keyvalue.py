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

from st2common.constants.keyvalue import USER_SEPARATOR

__all__ = [
    'InvalidUserKeyReferenceError',
]


class InvalidUserKeyReferenceError(ValueError):
    def __init__(self, ref):
        message = 'Invalid resource reference: %s' % (ref)
        self.ref = ref
        self.message = message
        super(InvalidUserKeyReferenceError, self).__init__(message)


class UserKeyReference(object):
    """
    Holds a reference to key given name and prefix. For example, if key name is foo and prefix
    is bob, this returns a string of form "bob.foo". This assumes '.' is the PREFIX_SEPARATOR.
    """

    def __init__(self, user, name):
        self._user = user
        self._name = name
        self.ref = ('%s%s%s' % (self._user, USER_SEPARATOR, self._name))

    def __str__(self):
        return self.ref

    @staticmethod
    def to_string_reference(user, name):
        """
        Given a key ``name`` and ``user``, this method returns a new name (string ref)
        to address the key value pair in the context of that user.

        :param user: User to whom key belongs.
        :type name: ``str``

        :param name: Original name of the key.
        :type name: ``str``

        :rtype: ``str``
        """
        if not user or not name:
            raise ValueError('Both "user" and "name" must be valid to generate ref.')
        return UserKeyReference(user=user, name=name).ref

    @staticmethod
    def from_string_reference(ref):
        """
        Given a user key ``reference``, this method returns the user and actual name of the key.

        :param ref: Reference to user key.
        :type ref: ``str``

        :rtype: ``tuple`` of ``str`` and ``str``
        """
        user = UserKeyReference.get_user(ref)
        name = UserKeyReference.get_name(ref)

        return (user, name)

    @staticmethod
    def get_user(ref):
        """
        Given a user key ``reference``, this method returns the user to whom the key belongs.

        :param ref: Reference to user key.
        :type ref: ``str``

        :rtype: ``str``
        """
        try:
            return ref.split(USER_SEPARATOR, 1)[0]
        except (IndexError, AttributeError):
            raise InvalidUserKeyReferenceError(ref=ref)

    @staticmethod
    def get_name(ref):
        """
        Given a user key ``reference``, this method returns the name of the key.

        :param ref: Reference to user key.
        :type ref: ``str``

        :rtype: ``str``
        """
        try:
            return ref.split(USER_SEPARATOR, 1)[1]
        except (IndexError, AttributeError):
            raise InvalidUserKeyReferenceError(ref=ref)
