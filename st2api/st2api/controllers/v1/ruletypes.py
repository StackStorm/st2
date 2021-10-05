# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mongoengine import ValidationError
import six

from st2common import log as logging
from st2common.models.api.rule import RuleTypeAPI
from st2common.persistence.rule import RuleType
from st2common.router import abort

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class RuleTypesController(object):
    """
    Implements the RESTful web endpoint that handles
    the lifecycle of a RuleType in the system.
    """

    @staticmethod
    def __get_by_id(id):
        try:
            return RuleType.get_by_id(id)
        except (ValueError, ValidationError) as e:
            msg = 'Database lookup for id="%s" resulted in exception. %s' % (id, e)
            LOG.exception(msg)
            abort(http_client.NOT_FOUND, msg)

    @staticmethod
    def __get_by_name(name):
        try:
            return [RuleType.get_by_name(name)]
        except ValueError as e:
            LOG.debug(
                'Database lookup for name="%s" resulted in exception : %s.', name, e
            )
            return []

    def get_one(self, id):
        """
        List RuleType objects by id.

        Handle:
            GET /ruletypes/1
        """
        ruletype_db = RuleTypesController.__get_by_id(id)
        ruletype_api = RuleTypeAPI.from_model(ruletype_db)
        return ruletype_api

    def get_all(self):
        """
        List all RuleType objects.

        Handles requests:
            GET /ruletypes/
        """
        ruletype_dbs = RuleType.get_all()
        ruletype_apis = [
            RuleTypeAPI.from_model(runnertype_db) for runnertype_db in ruletype_dbs
        ]
        return ruletype_apis


rule_types_controller = RuleTypesController()
