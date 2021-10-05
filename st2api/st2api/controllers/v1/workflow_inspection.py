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

from __future__ import absolute_import

import uuid

from orquesta.specs import loader as specs_loader
from oslo_config import cfg

from st2common import log as logging
from st2common import router
from st2common.services import workflows as workflow_service
from st2common.util import api as api_utils


LOG = logging.getLogger(__name__)


class WorkflowInspectionController(object):
    def mock_st2_ctx(self):
        st2_ctx = {
            "st2": {
                "api_url": api_utils.get_full_public_api_url(),
                "action_execution_id": uuid.uuid4().hex,
                "user": cfg.CONF.system_user.user,
            }
        }

        return st2_ctx

    def post(self, wf_def):
        # Load workflow definition into workflow spec model.
        spec_module = specs_loader.get_spec_module("native")
        wf_spec = spec_module.instantiate(wf_def)

        # Mock the st2 context that is typically passed to the workflow engine.
        st2_ctx = self.mock_st2_ctx()

        # Inspect the workflow spec and return the errors instead of raising exception.
        errors = workflow_service.inspect(wf_spec, st2_ctx, raise_exception=False)

        # Return the result of the inspection.
        return router.Response(json=errors)


workflow_inspection_controller = WorkflowInspectionController()
