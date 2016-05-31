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

import copy

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.api.action import RunnerTypeAPI
from st2common.persistence.runner import RunnerType
from st2common.util.action_db import get_runnertype_by_name
from st2common.constants.runners import LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT
from st2common.constants.runners import REMOTE_RUNNER_DEFAULT_ACTION_TIMEOUT
from st2common.constants.runners import REMOTE_RUNNER_DEFAULT_REMOTE_DIR
from st2common.constants.runners import PYTHON_RUNNER_DEFAULT_ACTION_TIMEOUT

__all__ = [
    'register_runner_types',
    'RUNNER_TYPES'
]


LOG = logging.getLogger(__name__)

RUNNER_TYPES = [
    {
        'name': 'local-shell-cmd',
        'aliases': ['run-local'],
        'description': 'A runner to execute local actions as a fixed user.',
        'enabled': True,
        'runner_parameters': {
            'cmd': {
                'description': 'Arbitrary Linux command to be executed on the '
                               'host.',
                'type': 'string'
            },
            'cwd': {
                'description': 'Working directory where the command will be executed in',
                'type': 'string'
            },
            'env': {
                'description': ('Environment variables which will be available to the command'
                                '(e.g. key1=val1,key2=val2)'),
                'type': 'object'
            },
            'sudo': {
                'description': 'The command will be executed with sudo.',
                'type': 'boolean',
                'default': False
            },
            'kwarg_op': {
                'description': 'Operator to use in front of keyword args i.e. "--" or "-".',
                'type': 'string',
                'default': '--'
            },
            'timeout': {
                'description': ('Action timeout in seconds. Action will get killed if it '
                                'doesn\'t finish in timeout seconds.'),
                'type': 'integer',
                'default': LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT
            }
        },
        'runner_module': 'st2actions.runners.localrunner'
    },
    {
        'name': 'local-shell-script',
        'aliases': ['run-local-script'],
        'description': 'A runner to execute local actions as a fixed user.',
        'enabled': True,
        'runner_parameters': {
            'cwd': {
                'description': 'Working directory where the script will be executed in',
                'type': 'string'
            },
            'env': {
                'description': ('Environment variables which will be available to the script'
                                '(e.g. key1=val1,key2=val2)'),
                'type': 'object'
            },
            'sudo': {
                'description': 'The command will be executed with sudo.',
                'type': 'boolean',
                'default': False
            },
            'kwarg_op': {
                'description': 'Operator to use in front of keyword args i.e. "--" or "-".',
                'type': 'string',
                'default': '--'
            },
            'timeout': {
                'description': ('Action timeout in seconds. Action will get killed if it '
                                'doesn\'t finish in timeout seconds.'),
                'type': 'integer',
                'default': LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT
            }
        },
        'runner_module': 'st2actions.runners.localrunner'
    },
    {
        'name': 'remote-shell-cmd',
        'aliases': ['run-remote'],
        'description': 'A remote execution runner that executes actions '
                       'as a fixed system user.',
        'enabled': True,
        'runner_parameters': {
            'hosts': {
                'description': 'A comma delimited string of a list of hosts '
                               'where the remote command will be executed.',
                'type': 'string',
                'required': True
            },
            'username': {
                'description': ('Username used to log-in. If not provided, '
                                'default username from config is used.'),
                'type': 'string',
                'required': False
            },
            'password': {
                'description': ('Password used to log in. If not provided, '
                                'private key from the config file is used.'),
                'type': 'string',
                'required': False,
                'secret': True
            },
            'private_key': {
                'description': ('Private key material or path to the private key file on disk '
                                'used to log in.'),
                'type': 'string',
                'required': False,
                'secret': True
            },
            'passphrase': {
                'description': ('Passphrase for the private key, if needed.'),
                'type': 'string',
                'required': False,
                'secret': True
            },
            'cmd': {
                'description': 'Arbitrary Linux command to be executed on the '
                               'remote host(s).',
                'type': 'string'
            },
            'cwd': {
                'description': 'Working directory where the script will be executed in',
                'type': 'string',
                'default': REMOTE_RUNNER_DEFAULT_REMOTE_DIR
            },
            'env': {
                'description': ('Environment variables which will be available to the command'
                                '(e.g. key1=val1,key2=val2)'),
                'type': 'object'
            },
            'parallel': {
                'description': 'Default to parallel execution.',
                'type': 'boolean',
                'default': False,
                'immutable': True
            },
            'sudo': {
                'description': 'The remote command will be executed with sudo.',
                'type': 'boolean',
                'default': False
            },
            'dir': {
                'description': 'The working directory where the script will be copied to ' +
                               'on the remote host.',
                'type': 'string',
                'default': REMOTE_RUNNER_DEFAULT_REMOTE_DIR,
                'immutable': True
            },
            'kwarg_op': {
                'description': 'Operator to use in front of keyword args i.e. "--" or "-".',
                'type': 'string',
                'default': '--'
            },
            'timeout': {
                'description': ('Action timeout in seconds. Action will get killed if it '
                                'doesn\'t finish in timeout seconds.'),
                'type': 'integer',
                'default': REMOTE_RUNNER_DEFAULT_ACTION_TIMEOUT
            },
            'port': {
                'description': 'SSH port. Note: This parameter is used only in ParamikoSSHRunner.',
                'type': 'integer',
                'default': 22,
                'required': False
            },
            'bastion_host': {
                'description': 'The host SSH connections will be proxied through. Note: This ' +
                               'connection is made using the same parameters as the final ' +
                               'connection, and is only used in ParamikoSSHRunner.',
                'type': 'string',
                'required': False
            }
        },
        'runner_module': 'st2actions.runners.remote_command_runner'
    },
    {
        'name': 'remote-shell-script',
        'aliases': ['run-remote-script'],
        'description': 'A remote execution runner that executes actions '
                       'as a fixed system user.',
        'enabled': True,
        'runner_parameters': {
            'hosts': {
                'description': 'A comma delimited string of a list of hosts '
                               'where the remote command will be executed.',
                'type': 'string',
                'required': True
            },
            'username': {
                'description': ('Username used to log-in. If not provided, '
                                'default username from config is used.'),
                'type': 'string',
                'required': False
            },
            'password': {
                'description': ('Password used to log in. If not provided, '
                                'private key from the config file is used.'),
                'type': 'string',
                'required': False,
                'secret': True
            },
            'private_key': {
                'description': ('Private key material to log in. Note: This needs to be actual '
                                'private key data and NOT path.'),
                'type': 'string',
                'required': False,
                'secret': True
            },
            'parallel': {
                'description': 'Default to parallel execution.',
                'type': 'boolean',
                'default': False,
                'immutable': True
            },
            'cwd': {
                'description': 'Working directory where the script will be executed in.',
                'type': 'string',
                'default': REMOTE_RUNNER_DEFAULT_REMOTE_DIR
            },
            'env': {
                'description': ('Environment variables which will be available to the script'
                                '(e.g. key1=val1,key2=val2)'),
                'type': 'object'
            },
            'sudo': {
                'description': 'The remote command will be executed with sudo.',
                'type': 'boolean',
                'default': False
            },
            'dir': {
                'description': 'The working directory where the script will be copied to ' +
                               'on the remote host.',
                'type': 'string',
                'default': REMOTE_RUNNER_DEFAULT_REMOTE_DIR
            },
            'kwarg_op': {
                'description': 'Operator to use in front of keyword args i.e. "--" or "-".',
                'type': 'string',
                'default': '--'
            },
            'timeout': {
                'description': ('Action timeout in seconds. Action will get killed if it '
                                'doesn\'t finish in timeout seconds.'),
                'type': 'integer',
                'default': REMOTE_RUNNER_DEFAULT_ACTION_TIMEOUT
            },
            'port': {
                'description': 'SSH port. Note: This parameter is used only in ParamikoSSHRunner.',
                'type': 'integer',
                'default': 22,
                'required': False
            },
            'bastion_host': {
                'description': 'The host SSH connections will be proxied through. Note: This ' +
                               'connection is made using the same parameters as the final ' +
                               'connection, and is only used in ParamikoSSHRunner.',
                'type': 'string',
                'required': False
            }
        },
        'runner_module': 'st2actions.runners.remote_script_runner'
    },
    {
        'name': 'http-request',
        'aliases': ['http-runner'],
        'description': 'A HTTP client for running HTTP actions.',
        'enabled': True,
        'runner_parameters': {
            'url': {
                'description': 'URL to the HTTP endpoint.',
                'type': 'string',
                'required': True
            },
            'headers': {
                'description': 'HTTP headers for the request.',
                'type': 'object'
            },
            'cookies': {
                'description': 'Optional cookies to send with the request.',
                'type': 'object'
            },
            'http_proxy': {
                'description': 'A URL of a HTTP proxy to use (e.g. http://10.10.1.10:3128).',
                'type': 'string'
            },
            'https_proxy': {
                'description': 'A URL of a HTTPs proxy to use (e.g. http://10.10.1.10:3128).',
                'type': 'string'
            },
            'allow_redirects': {
                'description': 'Set to True if POST/PUT/DELETE redirect following is allowed.',
                'type': 'boolean',
                'default': False
            },
            'verify_ssl_cert': {
                'description': 'Certificate for HTTPS request is verified by default using '
                               'requests CA bundle which comes from Mozilla. Verification '
                               'using a custom CA bundle is not yet supported. Set to False '
                               'to skip verification.',
                'type': 'boolean',
                'default': True
            }
        },
        'runner_module': 'st2actions.runners.httprunner'
    },
    {
        'name': 'mistral-v2',
        'aliases': [],
        'description': 'A runner for executing mistral v2 workflow.',
        'enabled': True,
        'runner_parameters': {
            'workflow': {
                'description': ('The name of the workflow to run if the entry_point is a '
                                'workbook of many workflows. The name should be in the '
                                'format "<pack_name>.<action_name>.<workflow_name>". '
                                'If entry point is a workflow or a workbook with a single '
                                'workflow, the runner will identify the workflow '
                                'automatically.'),
                'type': 'string'
            },
            'task': {
                'description': 'The name of the task to run for reverse workflow.',
                'type': 'string'
            },
            'context': {
                'description': 'Additional workflow inputs.',
                'type': 'object',
                'default': {}
            },
            'skip_notify': {
                'description': 'List of tasks to skip notifications for.',
                'type': 'array',
                'default': []
            }
        },
        'runner_module': 'st2actions.runners.mistral.v2',
        'query_module': 'st2actions.query.mistral.v2'
    },
    {
        'name': 'action-chain',
        'aliases': [],
        'description': 'A runner for launching linear action chains.',
        'enabled': True,
        'runner_parameters': {
            'skip_notify': {
                'description': 'List of tasks to skip notifications for.',
                'type': 'array',
                'default': []
            },
            'display_published': {
                'description': 'Intermediate published variables will be stored and displayed.',
                'type': 'boolean',
                'default': False
            }
        },
        'runner_module': 'st2actions.runners.actionchainrunner'
    },
    {
        'name': 'python-script',
        'aliases': ['run-python'],
        'description': 'A runner for launching python actions.',
        'enabled': True,
        'runner_parameters': {
            'env': {
                'description': ('Environment variables which will be available to the script'
                                '(e.g. key1=val1,key2=val2)'),
                'type': 'object'
            },
            'timeout': {
                'description': ('Action timeout in seconds. Action will get killed if it '
                                'doesn\'t finish in timeout seconds.'),
                'type': 'integer',
                'default': PYTHON_RUNNER_DEFAULT_ACTION_TIMEOUT
            }
        },
        'runner_module': 'st2actions.runners.pythonrunner'
    },

    # Experimental runners below
    {
        'name': 'announcement',
        'aliases': [],
        'description': 'A runner for emitting an announcement event on the stream.',
        'enabled': True,
        'runner_parameters': {
            'experimental': {
                'description': 'Flag to indicate acknowledment of using experimental runner',
                'type': 'boolean',
                'required': True,
                'default': False
            },
            'route': {
                'description': ('The routing_key used to route the message to consumers. '
                                'Might be a list of words, delimited by dots.'),
                'type': 'string',
                'default': 'general',
                'minLength': 1,
                'maxLength': 255
            }
        },
        'runner_module': 'st2actions.runners.announcementrunner'
    },
    {
        'name': 'windows-cmd',
        'aliases': [],
        'description': 'A remote execution runner that executes commands'
                       'on Windows hosts.',
        'experimental': False,
        'enabled': True,
        'runner_parameters': {
            'host': {
                'description': 'Host to execute the command on',
                'type': 'string',
                'required': True
            },
            'username': {
                'description': 'Username used to log-in.',
                'type': 'string',
                'default': 'Administrator',
                'required': True,
            },
            'password': {
                'description': 'Password used to log in.',
                'type': 'string',
                'required': True,
                'secret': True
            },
            'cmd': {
                'description': 'Arbitrary command to be executed on the '
                               'remote host.',
                'type': 'string'
            },
            'timeout': {
                'description': ('Action timeout in seconds. Action will get killed if it '
                                'doesn\'t finish in timeout seconds.'),
                'type': 'integer',
                'default': REMOTE_RUNNER_DEFAULT_ACTION_TIMEOUT
            }
        },
        'runner_module': 'st2actions.runners.windows_command_runner'
    },
    {
        'name': 'windows-script',
        'aliases': [],
        'description': 'A remote execution runner that executes power shell scripts'
                       'on Windows hosts.',
        'enabled': True,
        'experimental': False,
        'runner_parameters': {
            'host': {
                'description': 'Host to execute the command on',
                'type': 'string',
                'required': True
            },
            'username': {
                'description': 'Username used to log-in.',
                'type': 'string',
                'default': 'Administrator',
                'required': True,
            },
            'password': {
                'description': 'Password used to log in.',
                'type': 'string',
                'required': True,
                'secret': True
            },
            'share': {
                'description': 'Name of the Windows share where script files are uploaded',
                'type': 'string',
                'required': True,
                'default': 'C$'
            },
            'timeout': {
                'description': ('Action timeout in seconds. Action will get killed if it '
                                'doesn\'t finish in timeout seconds.'),
                'type': 'integer',
                'default': REMOTE_RUNNER_DEFAULT_ACTION_TIMEOUT
            }
        },
        'runner_module': 'st2actions.runners.windows_script_runner'
    },
    {
        'name': 'cloudslang',
        'aliases': [],
        'description': 'A runner to execute cloudslang flows.',
        'enabled': True,
        'runner_parameters': {
            'inputs': {
                'description': ('Inputs which will be available to CLoudSlang flow execution'
                                '(e.g. input1=val1,input2=val2)'),
                'type': 'object',
                'default': {}
            },
            'timeout': {
                'description': ('Action timeout in seconds. Action will get killed if it '
                                'doesn\'t finish in timeout seconds.'),
                'type': 'integer',
                'default': LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT
            }
        },
        'runner_module': 'st2actions.runners.cloudslang.cloudslang_runner'
    },
    {
        'name': 'noop',
        'aliases': [],
        'description': 'A runner that returns a static response regardless of input parameters',
        'enabled': True,
        'runner_parameters': {},
        'runner_module': 'st2actions.runners.nooprunner'
    }
]


def register_runner_types(experimental=False):
    """
    :param experimental: True to also register experimental runners.
    :type experimental: ``bool``
    """
    LOG.debug('Start : register default RunnerTypes.')

    for runner_type in RUNNER_TYPES:
        runner_type = copy.deepcopy(runner_type)

        # For backward compatibility reasons, we also register runners under the old names
        runner_names = [runner_type['name']] + runner_type.get('aliases', [])
        for runner_name in runner_names:
            runner_type['name'] = runner_name
            runner_experimental = runner_type.get('experimental', False)

            if runner_experimental and not experimental:
                LOG.debug('Skipping experimental runner "%s"' % (runner_name))
                continue

            # Remove additional, non db-model attributes
            non_db_attributes = ['experimental', 'aliases']
            for attribute in non_db_attributes:
                if attribute in runner_type:
                    del runner_type[attribute]

            try:
                runner_type_db = get_runnertype_by_name(runner_name)
                update = True
            except StackStormDBObjectNotFoundError:
                runner_type_db = None
                update = False

            # Note: We don't want to overwrite "enabled" attribute which is already in the database
            # (aka we don't want to re-enable runner which has been disabled by the user)
            if runner_type_db and runner_type_db['enabled'] != runner_type['enabled']:
                runner_type['enabled'] = runner_type_db['enabled']

            runner_type_api = RunnerTypeAPI(**runner_type)
            runner_type_api.validate()
            runner_type_model = RunnerTypeAPI.to_model(runner_type_api)

            if runner_type_db:
                runner_type_model.id = runner_type_db.id

            try:
                runner_type_db = RunnerType.add_or_update(runner_type_model)

                extra = {'runner_type_db': runner_type_db}
                if update:
                    LOG.audit('RunnerType updated. RunnerType %s', runner_type_db, extra=extra)
                else:
                    LOG.audit('RunnerType created. RunnerType %s', runner_type_db, extra=extra)
            except Exception:
                LOG.exception('Unable to register runner type %s.', runner_type['name'])

    LOG.debug('End : register default RunnerTypes.')
