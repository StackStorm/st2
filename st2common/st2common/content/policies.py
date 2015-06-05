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

import glob
import os
import six
import sys

import st2common.content.utils as content_utils

from st2common import log as logging
from st2common.constants.meta import ALLOWED_EXTS
from st2common.bootstrap.base import ResourceRegistrar
from st2common.models.api.policy import PolicyTypeAPI, PolicyAPI
from st2common.persistence.policy import PolicyType, Policy
from st2common.util import loader


__all__ = [
    'PolicyRegistrar',
    'register_policy_types',
    'register_policies'
]


LOG = logging.getLogger(__name__)


class PolicyRegistrar(ResourceRegistrar):
    ALLOWED_EXTENSIONS = ALLOWED_EXTS

    def register_policies_from_packs(self, base_dirs):
        """
        Discover all the packs in the provided directory and register policies from all of the
        discovered packs.

        :return: Number of policies registered.
        :rtype: ``int``
        """
        registered_count = 0

        content = self._pack_loader.get_content(base_dirs=base_dirs,
                                                content_type='policies')

        for pack, policies_dir in six.iteritems(content):
            try:
                LOG.debug('Registering policies from pack %s:, dir: %s', pack, policies_dir)
                policies = self._get_policies_from_pack(policies_dir)
                count = self._register_policies_from_pack(pack=pack, policies=policies)
                registered_count += count
            except:
                LOG.exception('Failed registering all policies from pack: %s', policies_dir)

        return registered_count

    def register_policies_from_pack(self, pack_dir):
        """
        Register all the policies from the provided pack.
        :return: Number of policies registered.

        :rtype: ``int``
        """
        pack_dir = pack_dir[:-1] if pack_dir.endswith('/') else pack_dir
        _, pack = os.path.split(pack_dir)
        policies_dir = self._pack_loader.get_content_from_pack(pack_dir=pack_dir,
                                                               content_type='policies')

        registered_count = 0

        if not policies_dir:
            return registered_count

        LOG.debug('Registering policies from pack %s:, dir: %s', pack, policies_dir)

        try:
            policies = self._get_policies_from_pack(policies_dir=policies_dir)
            registered_count = self._register_policies_from_pack(pack=pack, policies=policies)
        except:
            LOG.exception('Failed registering all policies from pack: %s', policies_dir)
            return 0

        return registered_count

    def _get_policies_from_pack(self, policies_dir):
        return self.get_resources_from_pack(resources_dir=policies_dir)

    def _register_policies_from_pack(self, pack, policies):
        registered_count = 0

        for policy in policies:
            try:
                LOG.debug('Loading policy from %s.', policy)
                self._register_policy(pack, policy)
            except Exception:
                LOG.exception('Unable to register policy: %s', policy)
                continue
            else:
                registered_count += 1

        return registered_count

    def _register_policy(self, pack, policy):
        content = self._meta_loader.load(policy)
        pack_field = content.get('pack', None)
        if not pack_field:
            content['pack'] = pack
            pack_field = pack
        if pack_field != pack:
            raise Exception('Model is in pack "%s" but field "pack" is different: %s' %
                            (pack, pack_field))

        policy_api = PolicyAPI(**content)
        policy_api.validate()
        policy_db = PolicyAPI.to_model(policy_api)

        try:
            policy_db.id = Policy.get_by_name(policy_api.name).id
        except ValueError:
            LOG.debug('Policy "%s" is not found. Creating new entry.', policy)

        try:
            policy_db = Policy.add_or_update(policy_db)
            extra = {'policy_db': policy_db}
            LOG.audit('Policy "%s" is updated.', policy_db.ref, extra=extra)
        except Exception:
            LOG.exception('Failed to create policy %s.', policy_api.name)
            raise


def register_policy_types(module):
    registered_count = 0
    mod_path = os.path.dirname(os.path.realpath(sys.modules[module.__name__].__file__))
    path = '%s/policies/meta' % mod_path

    files = []
    for ext in ALLOWED_EXTS:
        exp = '%s/*%s' % (path, ext)
        files += glob.glob(exp)

    for f in files:
        try:
            LOG.debug('Loading policy type from "%s".', f)
            content = loader.load_meta_file(f)
            policy_type_api = PolicyTypeAPI(**content)
            policy_type_db = PolicyTypeAPI.to_model(policy_type_api)

            try:
                existing_entry = PolicyType.get_by_ref(policy_type_db.ref)
                if existing_entry:
                    policy_type_db.id = existing_entry.id
            except ValueError:
                LOG.debug('Policy type "%s" is not found. Creating new entry.',
                          policy_type_db.ref)

            policy_type_db = PolicyType.add_or_update(policy_type_db)
            extra = {'policy_type_db': policy_type_db}
            LOG.audit('Policy type "%s" is updated.', policy_type_db.ref, extra=extra)

            registered_count += 1
        except:
            LOG.exception('Unable to register policy type from "%s".', f)

    return registered_count


def register_policies(packs_base_paths=None, pack_dir=None):
    if packs_base_paths:
        assert(isinstance(packs_base_paths, list))

    if not packs_base_paths:
        packs_base_paths = content_utils.get_packs_base_paths()

    registrar = PolicyRegistrar()

    if pack_dir:
        result = registrar.register_policies_from_pack(pack_dir=pack_dir)
    else:
        result = registrar.register_policies_from_packs(base_dirs=packs_base_paths)

    return result
