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

import re

from collections import defaultdict
from collections import OrderedDict

import pecan
from pecan.rest import RestController
import six

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
from st2common.models.api.base import jsexpose
from st2api.controllers.resource import ResourceController
from st2api.controllers.v1.actionexecutions import ActionExecutionsControllerMixin
from st2common.models.api.action import LiveActionCreateAPI
from st2common.models.api.pack import PackAPI
from st2common.models.api.pack import PackInstallRequestAPI
from st2common.models.api.pack import PackRegisterRequestAPI
from st2common.models.api.pack import PackSearchRequestAPI
from st2common.models.api.pack import PackAsyncAPI
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.pack import Pack
from st2common.rbac.types import PermissionType
from st2common.rbac.decorators import request_user_has_permission
from st2common.rbac.decorators import request_user_has_resource_db_permission
from st2common.services import packs as packs_service

http_client = six.moves.http_client

__all__ = [
    'PacksController',
    'BasePacksController',
    'ENTITIES'
]

LOG = logging.getLogger(__name__)

# Note: The order those are defined it's important so they are registered in the same order as
# they are in st2-register-content.
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


class PackInstallController(ActionExecutionsControllerMixin, RestController):

    @request_user_has_permission(permission_type=PermissionType.PACK_INSTALL)
    @jsexpose(body_cls=PackInstallRequestAPI, status_code=http_client.ACCEPTED)
    def post(self, pack_install_request):
        parameters = {
            'packs': pack_install_request.packs,
        }

        if pack_install_request.force:
            parameters['force'] = True

        new_liveaction_api = LiveActionCreateAPI(action='packs.install',
                                                 parameters=parameters,
                                                 user=None)

        execution = self._handle_schedule_execution(liveaction_api=new_liveaction_api)

        return PackAsyncAPI(execution_id=execution.id)


class PackUninstallController(ActionExecutionsControllerMixin, RestController):

    @request_user_has_permission(permission_type=PermissionType.PACK_UNINSTALL)
    @jsexpose(body_cls=PackInstallRequestAPI, arg_types=[str], status_code=http_client.ACCEPTED)
    def post(self, pack_uninstall_request, ref_or_id=None):
        if ref_or_id:
            parameters = {
                'packs': [ref_or_id]
            }
        else:
            parameters = {
                'packs': pack_uninstall_request.packs
            }

        new_liveaction_api = LiveActionCreateAPI(action='packs.uninstall',
                                                 parameters=parameters,
                                                 user=None)

        execution = self._handle_schedule_execution(liveaction_api=new_liveaction_api)

        return PackAsyncAPI(execution_id=execution.id)


class PackRegisterController(RestController):

    @request_user_has_permission(permission_type=PermissionType.PACK_REGISTER)
    @jsexpose(body_cls=PackRegisterRequestAPI)
    def post(self, pack_register_request):
        if pack_register_request and hasattr(pack_register_request, 'types'):
            types = pack_register_request.types
        else:
            types = ['runner', 'action', 'trigger', 'sensor', 'rule', 'rule_type', 'alias',
                     'policy_type', 'policy', 'config']

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
                                      fail_on_failure=fail_on_failure)
                if packs:
                    for pack in packs:
                        pack_path = content_utils.get_pack_base_path(pack)

                        try:
                            registered_count = registrar.register_from_pack(pack_dir=pack_path)
                            result[name] += registered_count
                        except ValueError as e:
                            # Throw more user-friendly exception if requsted pack doesn't exist
                            if re.match('Directory ".*?" doesn\'t exist', str(e)):
                                msg = 'Pack "%s" not found on disk: %s' % (pack, str(e))
                                raise ValueError(msg)

                            raise e
                else:
                    packs_base_paths = content_utils.get_packs_base_paths()
                    registered_count = registrar.register_from_packs(base_dirs=packs_base_paths)
                    result[name] += registered_count

        return result


class PackSearchController(RestController):

    @request_user_has_permission(permission_type=PermissionType.PACK_SEARCH)
    @jsexpose(body_cls=PackSearchRequestAPI)
    def post(self, pack_search_request):
        if hasattr(pack_search_request, 'query'):
            packs = packs_service.search_pack_index(pack_search_request.query,
                                                    case_sensitive=False)
            return [PackAPI(**pack) for pack in packs]
        else:
            pack = packs_service.get_pack_from_index(pack_search_request.pack)
            return PackAPI(**pack) if pack else None


class IndexHealthController(RestController):

    @request_user_has_permission(permission_type=PermissionType.PACK_VIEW_INDEX_HEALTH)
    @jsexpose()
    def get(self):
        """
        Check if all listed indexes are healthy: they should be reachable,
        return valid JSON objects, and yield more than one result.
        """
        _, status = packs_service.fetch_pack_index(allow_empty=True)

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

    def _get_one_by_ref_or_id(self, ref_or_id, exclude_fields=None):
        LOG.info('GET %s with ref_or_id=%s', pecan.request.path, ref_or_id)

        instance = self._get_by_ref_or_id(ref_or_id=ref_or_id, exclude_fields=exclude_fields)

        if not instance:
            msg = 'Unable to identify resource with ref_or_id "%s".' % (ref_or_id)
            pecan.abort(http_client.NOT_FOUND, msg)
            return

        from_model_kwargs = self._get_from_model_kwargs_for_request(request=pecan.request)
        result = self.model.from_model(instance, **from_model_kwargs)
        LOG.debug('GET %s with ref_or_id=%s, client_result=%s', pecan.request.path, ref_or_id,
                  result)

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


class PacksIndexController(RestController):
    search = PackSearchController()
    health = IndexHealthController()


class PacksController(BasePacksController):
    from st2api.controllers.v1.packviews import PackViewsController

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

    @request_user_has_permission(permission_type=PermissionType.PACK_LIST)
    @jsexpose()
    def get_all(self, **kwargs):
        return super(PacksController, self)._get_all(**kwargs)

    @request_user_has_resource_db_permission(permission_type=PermissionType.PACK_VIEW)
    @jsexpose(arg_types=[str])
    def get_one(self, ref_or_id):
        return self._get_one_by_ref_or_id(ref_or_id=ref_or_id)
