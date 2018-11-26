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

try:
    from mistralclient.api import client as mistral
except ImportError:
    # Likely running on installation without Mistral
    mistral = None

import six

from st2common import log as logging
from st2common.router import Response
from st2common.router import abort
from st2common.validators.workflow.mistral import v2 as mistral_validation_utils


LOG = logging.getLogger(__name__)

http_client = six.moves.http_client


class MistralValidationController(object):

    def __init__(self):
        super(MistralValidationController, self).__init__()
        self.validator = mistral_validation_utils.get_validator()

    def post(self, def_yaml):
        if not mistral:
            abort(http_client.NOT_FOUND)
            return

        result = self.validator.validate(def_yaml)

        for error in result:
            if not error.get('path', None):
                error['path'] = ''

        return Response(json=result)


mistral_validation_controller = MistralValidationController()
