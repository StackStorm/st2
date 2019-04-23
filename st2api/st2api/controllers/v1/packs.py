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

import os
import re

from collections import defaultdict
from collections import OrderedDict

import six
from oslo_config import cfg

import st2common
from st2common import log as logging
from st2common.bootstrap.triggersregistrar import TriggersRegistrar
from st2common.bootstrap.sensorsregistrar import SensorsRegistrar
from st2common.bootstrap.actionsregistrar import ActionsRegistrar
from st2common.bootstrap.aliasesregistrar import AliasesRegistrar
from st2common.bootstrap.policiesregistrar import PolicyRegistrar
import st2common.bootstrap.policiesregistrar as policies_registrar
import st2common.bootstrap.runnersregistrar as runners_registrar
from st2common.bootstrap.rulesregistrar import RulesRegistrar
import st2common.bootstrap.ruletypesregistrar as rule_types_registrar
from st2common.bootstrap.configsregistrar import ConfigsRegistrar
import st2common.content.utils as content_utils
from st2common.models.db.auth import UserDB
from st2common.models.api.action import LiveActionCreateAPI
from st2common.models.api.pack import PackAPI
from st2common.models.api.pack import PackAsyncAPI
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.pack import Pack
from st2common.rbac.types import PermissionType
from st2common.rbac.backends import get_rbac_backend
from st2common.services import packs as packs_service
from st2common.router import abort
from st2common.router import Response

from st2api.controllers.resource import ResourceController
from st2api.controllers.v1.actionexecutions import ActionExecutionsControllerMixin

http_client = six.moves.http_client

__all__ = [
    'PacksController',
    'BasePacksController',
    'ENTITIES'
]

LOG = logging.getLogger(__name__)

# Note: The order those are defined it's important so they are registered in
# the same order as they are in st2-register-content.
# We also need to use list of tuples to preserve the order.
ENTITIES = OrderedDict([
    ('trigger', (TriggersRegistrar, 'triggers')),
    ('sensor', (SensorsRegistrar, 'sensors')),
    ('action', (ActionsRegistrar, 'actions')),
    ('rule', (RulesRegistrar, 'rules')),
    ('alias', (AliasesRegistrar, 'aliases')),
    ('policy', (PolicyRegistrar, 'policies')),
    ('config', (ConfigsRegistrar, 'configs'))
])


def _get_proxy_config():
    LOG.debug('Loading proxy configuration from env variables %s.', os.environ)
    http_proxy = os.environ.get('http_proxy', None)
    https_proxy = os.environ.get('https_proxy', None)
    no_proxy = os.environ.get('no_proxy', None)
    proxy_ca_bundle_path = os.environ.get('proxy_ca_bundle_path', None)

    proxy_config = {
        'http_proxy': http_proxy,
        'https_proxy': https_proxy,
        'proxy_ca_bundle_path': proxy_ca_bundle_path,
        'no_proxy': no_proxy
    }

    LOG.debug('Proxy configuration: %s', proxy_config)

    return proxy_config


class PackInstallController(ActionExecutionsControllerMixin):

    def post(self, pack_install_request, requester_user=None):
        parameters = {
            'packs': pack_install_request.packs,
            'python3': pack_install_request.python3
        }

        if pack_install_request.force:
            parameters['force'] = True

        if not requester_user:
            requester_user = UserDB(cfg.CONF.system_user.user)

        new_liveaction_api = LiveActionCreateAPI(action='packs.install',
                                                 parameters=parameters,
                                                 user=requester_user.name)

        execution_resp = self._handle_schedule_execution(liveaction_api=new_liveaction_api,
                                                         requester_user=requester_user)

        exec_id = PackAsyncAPI(execution_id=execution_resp.json['id'])

        return Response(json=exec_id, status=http_client.ACCEPTED)


class PackUninstallController(ActionExecutionsControllerMixin):

    def post(self, pack_uninstall_request, ref_or_id=None, requester_user=None):
        if ref_or_id:
            parameters = {
                'packs': [ref_or_id]
            }
        else:
            parameters = {
                'packs': pack_uninstall_request.packs
            }

        if not requester_user:
            requester_user = UserDB(cfg.CONF.system_user.user)

        new_liveaction_api = LiveActionCreateAPI(action='packs.uninstall',
                                                 parameters=parameters,
                                                 user=requester_user.name)

        execution_resp = self._handle_schedule_execution(liveaction_api=new_liveaction_api,
                                                         requester_user=requester_user)

        exec_id = PackAsyncAPI(execution_id=execution_resp.json['id'])

        return Response(json=exec_id, status=http_client.ACCEPTED)


class PackRegisterController(object):
    CONTENT_TYPES = ['runner', 'action', 'trigger', 'sensor', 'rule',
                     'rule_type', 'alias', 'policy_type', 'policy', 'config']

    def post(self, pack_register_request):
        if pack_register_request and hasattr(pack_register_request, 'types'):
            types = pack_register_request.types
            if 'all' in types:
                types = PackRegisterController.CONTENT_TYPES
        else:
            types = PackRegisterController.CONTENT_TYPES

        if pack_register_request and hasattr(pack_register_request, 'packs'):
            packs = list(set(pack_register_request.packs))
        else:
            packs = None

        result = defaultdict(int)

        # Register depended resources (actions depend on runners, rules depend on rule types, etc)
        if ('runner' in types or 'runners' in types) or ('action' in types or 'actions' in types):
            result['runners'] = runners_registrar.register_runners(experimental=True)
        if ('rule_type' in types or 'rule_types' in types) or \
           ('rule' in types or 'rules' in types):
            result['rule_types'] = rule_types_registrar.register_rule_types()
        if ('policy_type' in types or 'policy_types' in types) or \
           ('policy' in types or 'policies' in types):
            result['policy_types'] = policies_registrar.register_policy_types(st2common)

        use_pack_cache = False

        fail_on_failure = getattr(pack_register_request, 'fail_on_failure', True)
        for type, (Registrar, name) in six.iteritems(ENTITIES):
            if type in types or name in types:
                registrar = Registrar(use_pack_cache=use_pack_cache,
                                      use_runners_cache=True,
                                      fail_on_failure=fail_on_failure)
                if packs:
                    for pack in packs:
                        pack_path = content_utils.get_pack_base_path(pack)

                        try:
                            registered_count = registrar.register_from_pack(pack_dir=pack_path)
                            result[name] += registered_count
                        except ValueError as e:
                            # Throw more user-friendly exception if requsted pack doesn't exist
                            if re.match('Directory ".*?" doesn\'t exist', six.text_type(e)):
                                msg = 'Pack "%s" not found on disk: %s' % (pack, six.text_type(e))
                                raise ValueError(msg)

                            raise e
                else:
                    packs_base_paths = content_utils.get_packs_base_paths()
                    registered_count = registrar.register_from_packs(base_dirs=packs_base_paths)
                    result[name] += registered_count

        return result


class PackSearchController(object):

    def post(self, pack_search_request):

        proxy_config = _get_proxy_config()

        if hasattr(pack_search_request, 'query'):
            packs = packs_service.search_pack_index(pack_search_request.query,
                                                    case_sensitive=False,
                                                    proxy_config=proxy_config)
            return [PackAPI(**pack) for pack in packs]
        else:
            pack = packs_service.get_pack_from_index(pack_search_request.pack,
                                                     proxy_config=proxy_config)
            return PackAPI(**pack) if pack else []


class IndexHealthController(object):

    def get(self):
        """
        Check if all listed indexes are healthy: they should be reachable,
        return valid JSON objects, and yield more than one result.
        """
        proxy_config = _get_proxy_config()

        _, status = packs_service.fetch_pack_index(allow_empty=True, proxy_config=proxy_config)

        health = {
            "indexes": {
                "count": len(status),
                "valid": 0,
                "invalid": 0,
                "errors": {},
                "status": status,
            },
            "packs": {
                "count": 0,
            },
        }

        for index in status:
            if index['error']:
                error_count = health['indexes']['errors'].get(index['error'], 0) + 1
                health['indexes']['invalid'] += 1
                health['indexes']['errors'][index['error']] = error_count
            else:
                health['indexes']['valid'] += 1
            health['packs']['count'] += index['packs']

        return health


class BasePacksController(ResourceController):
    model = PackAPI
    access = Pack

    def _get_one_by_ref_or_id(self, ref_or_id, requester_user, exclude_fields=None):
        instance = self._get_by_ref_or_id(ref_or_id=ref_or_id, exclude_fields=exclude_fields)

        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=instance,
                                                          permission_type=PermissionType.PACK_VIEW)

        if not instance:
            msg = 'Unable to identify resource with ref_or_id "%s".' % (ref_or_id)
            abort(http_client.NOT_FOUND, msg)
            return

        result = self.model.from_model(instance, **self.from_model_kwargs)

        return result

    def _get_by_ref_or_id(self, ref_or_id, exclude_fields=None):
        resource_db = self._get_by_id(resource_id=ref_or_id, exclude_fields=exclude_fields)

        if not resource_db:
            # Try ref
            resource_db = self._get_by_ref(ref=ref_or_id, exclude_fields=exclude_fields)

        if not resource_db:
            msg = 'Resource with a ref or id "%s" not found' % (ref_or_id)
            raise StackStormDBObjectNotFoundError(msg)

        return resource_db

    def _get_by_ref(self, ref, exclude_fields=None):
        """
        Note: In this case "ref" is pack name and not StackStorm's ResourceReference.
        """
        resource_db = self.access.query(ref=ref, exclude_fields=exclude_fields).first()
        return resource_db


class PacksIndexController():
    search = PackSearchController()
    health = IndexHealthController()

    def get_all(self):
        proxy_config = _get_proxy_config()

        index, status = packs_service.fetch_pack_index(proxy_config=proxy_config)

        return {
            'status': status,
            'index': index
        }


class PacksController(BasePacksController):
    from st2api.controllers.v1.pack_views import PackViewsController

    model = PackAPI
    access = Pack
    supported_filters = {
        'name': 'name',
        'ref': 'ref'
    }

    query_options = {
        'sort': ['ref']
    }

    # Nested controllers
    install = PackInstallController()
    uninstall = PackUninstallController()
    register = PackRegisterController()
    views = PackViewsController()
    index = PacksIndexController()

    def __init__(self):
        super(PacksController, self).__init__()
        self.get_one_db_method = self._get_by_ref_or_id

    def get_all(self, exclude_attributes=None, include_attributes=None, sort=None, offset=0,
                limit=None, requester_user=None, **raw_filters):
        return super(PacksController, self)._get_all(exclude_fields=exclude_attributes,
                                                     include_fields=include_attributes,
                                                     sort=sort,
                                                     offset=offset,
                                                     limit=limit,
                                                     raw_filters=raw_filters,
                                                     requester_user=requester_user)

    def get_one(self, ref_or_id, requester_user):
        return self._get_one_by_ref_or_id(ref_or_id=ref_or_id, requester_user=requester_user)


packs_controller = PacksController()
