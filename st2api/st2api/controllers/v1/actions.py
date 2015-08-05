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
import os.path

import six
from pecan import abort
from mongoengine import ValidationError

# TODO: Encapsulate mongoengine errors in our persistence layer. Exceptions
#       that bubble up to this layer should be core Python exceptions or
#       StackStorm defined exceptions.

from st2api.controllers import resource
from st2api.controllers.v1.actionviews import ActionViewsController
from st2common import log as logging
from st2common.constants.pack import DEFAULT_PACK_NAME
from st2common.constants.triggers import ACTION_FILE_WRITTEN_TRIGGER
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.models.api.base import jsexpose
from st2common.persistence.action import Action
from st2common.models.api.action import ActionAPI
from st2common.models.api.action import ActionCreateAPI
from st2common.validators.api.misc import validate_not_part_of_system_pack
from st2common.content.utils import get_pack_base_path
from st2common.content.utils import get_pack_resource_file_abs_path
from st2common.transport.reactor import TriggerDispatcher
from st2common.util.system_info import get_host_info
import st2common.validators.api.action as action_validator

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class ActionsController(resource.ContentPackResourceController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Actions in the system.
    """
    views = ActionViewsController()

    model = ActionAPI
    access = Action
    supported_filters = {
        'name': 'name',
        'pack': 'pack'
    }

    query_options = {
        'sort': ['pack', 'name']
    }

    include_reference = True

    def __init__(self, *args, **kwargs):
        super(ActionsController, self).__init__(*args, **kwargs)
        self._trigger_dispatcher = TriggerDispatcher(LOG)

    @jsexpose(body_cls=ActionCreateAPI, status_code=http_client.CREATED)
    def post(self, action):
        """
            Create a new action.

            Handles requests:
                POST /actions/
        """
        if not hasattr(action, 'pack'):
            setattr(action, 'pack', DEFAULT_PACK_NAME)

        try:
            validate_not_part_of_system_pack(action)
        except ValueValidationException as e:
            abort(http_client.BAD_REQUEST, str(e))

        try:
            action_validator.validate_action(action)
        except ValueValidationException as e:
            abort(http_client.BAD_REQUEST, str(e))
            return

        # Write pack data files to disk (if any are provided)
        data_files = getattr(action, 'data_files', [])
        written_data_files = []
        if data_files:
            written_data_files = self._handle_data_files(pack_name=action.pack,
                                                         data_files=data_files)

        action_model = ActionAPI.to_model(action)

        LOG.debug('/actions/ POST verified ActionAPI object=%s', action)
        action_db = Action.add_or_update(action_model)
        LOG.debug('/actions/ POST saved ActionDB object=%s', action_db)

        # Dispatch an internal trigger for each written data file. This way user
        # automate comitting this files to git using StackStorm rule
        if written_data_files:
            self._dispatch_trigger_for_written_data_files(action_db=action_db,
                                                          written_data_files=written_data_files)

        extra = {'acion_db': action_db}
        LOG.audit('Action created. Action.id=%s' % (action_db.id), extra=extra)
        action_api = ActionAPI.from_model(action_db)

        return action_api

    @jsexpose(arg_types=[str], body_cls=ActionCreateAPI)
    def put(self, action_ref_or_id, action):
        action_db = self._get_by_ref_or_id(ref_or_id=action_ref_or_id)
        action_id = action_db.id

        try:
            validate_not_part_of_system_pack(action_db)
        except ValueValidationException as e:
            abort(http_client.BAD_REQUEST, str(e))

        if not getattr(action, 'pack', None):
            action.pack = action_db.pack

        try:
            action_validator.validate_action(action)
        except ValueValidationException as e:
            abort(http_client.BAD_REQUEST, str(e))
            return

        # Write pack data files to disk (if any are provided)
        data_files = getattr(action, 'data_files', [])
        written_data_files = []
        if data_files:
            written_data_files = self._handle_data_files(pack_name=action.pack,
                                                         data_files=data_files)

        try:
            action_db = ActionAPI.to_model(action)
            action_db.id = action_id
            action_db = Action.add_or_update(action_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Unable to update action data=%s', action)
            abort(http_client.BAD_REQUEST, str(e))
            return

        action_api = ActionAPI.from_model(action_db)
        LOG.debug('PUT /actions/ client_result=%s', action_api)

        return action_api

    @jsexpose(arg_types=[str], status_code=http_client.NO_CONTENT)
    def delete(self, action_ref_or_id):
        """
            Delete an action.

            Handles requests:
                POST /actions/1?_method=delete
                DELETE /actions/1
                DELETE /actions/mypack.myaction
        """
        action_db = self._get_by_ref_or_id(ref_or_id=action_ref_or_id)
        action_id = action_db.id

        try:
            validate_not_part_of_system_pack(action_db)
        except ValueValidationException as e:
            abort(http_client.BAD_REQUEST, str(e))

        LOG.debug('DELETE /actions/ lookup with ref_or_id=%s found object: %s',
                  action_ref_or_id, action_db)

        try:
            Action.delete(action_db)
        except Exception as e:
            LOG.error('Database delete encountered exception during delete of id="%s". '
                      'Exception was %s', action_id, e)
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return

        extra = {'action_db': action_db}
        LOG.audit('Action deleted. Action.id=%s' % (action_db.id), extra=extra)
        return None

    def _handle_data_files(self, pack_name, data_files):
        """
        Method for handling action data files and writing them on disk.
        """
        written_file_paths = []
        for data_file in data_files:
            file_path = data_file['file_path']
            content = data_file['content']

            file_path = get_pack_resource_file_abs_path(pack_name=pack_name,
                                                        resource_type='action',
                                                        file_path=file_path)

            LOG.debug('Writing data file "%s" to "%s"' % (str(data_file), file_path))
            self._write_data_file(pack_name=pack_name, file_path=file_path, content=content)
            written_file_paths.append(file_path)

        return written_file_paths

    def _write_data_file(self, pack_name, file_path, content):
        """
        Write data file on disk.
        """
        # Throw if pack directory doesn't exist
        pack_base_path = get_pack_base_path(pack_name=pack_name)
        if not os.path.isdir(pack_base_path):
            raise ValueError('Directory for pack "%s" doesn\'t exist' % (pack_name))

        # Create pack sub-directory tree if it doesn't exist
        directory = os.path.dirname(file_path)

        if not os.path.isdir(directory):
            os.makedirs(directory)

        with open(file_path, 'w') as fp:
            fp.write(content)

    def _dispatch_trigger_for_written_data_files(self, action_db, written_data_files):
        trigger = ACTION_FILE_WRITTEN_TRIGGER['name']
        host_info = get_host_info()

        for file_path in written_data_files:
            payload = {
                'ref': action_db.ref,
                'file_path': file_path,
                'host_info': host_info
            }
            self._trigger_dispatcher.dispatch(trigger=trigger, payload=payload)
