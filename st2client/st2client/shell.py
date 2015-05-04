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

"""
Command-line interface to StackStorm.
"""

from __future__ import print_function

import os
import sys
import json
import time
import argparse
import calendar
import logging
import traceback
from collections import defaultdict

import six
from six.moves.configparser import ConfigParser

from st2client import __version__
from st2client import models
from st2client.client import Client
from st2client.commands import resource
from st2client.commands import access
from st2client.commands import sensor
from st2client.commands import trigger
from st2client.commands import action
from st2client.commands import datastore
from st2client.commands import webhook
from st2client.exceptions.operations import OperationFailureException
from st2client.utils.date import parse as parse_isotime
from st2client.utils.misc import merge_dicts

__all__ = [
    'Shell'
]


LOG = logging.getLogger(__name__)

DEFAULT_RC_FILE_PATH = '~/.st2rc'
DEFAULT_RC_FILE_PATH = os.path.expanduser(DEFAULT_RC_FILE_PATH)

ST2_CONFIG_DIRECTORY = '~/.st2'
ST2_CONFIG_DIRECTORY = os.path.expanduser(ST2_CONFIG_DIRECTORY)
CACHED_TOKEN_PATH = os.path.join(ST2_CONFIG_DIRECTORY, 'token')


RC_FILE_OPTIONS = {
    'general': {
        'base_url': {
            'type': 'string',
            'default': None
        },
        'api_version': {
            'type': 'string',
            'default': None
        },
        'cacert': {
            'type': 'string',
            'default': None
        }
    },
    'cli': {
        'debug': {
            'type': 'bool',
            'default': False
        },
        'cache_token': {
            'type': 'boolean',
            'default': True
        }
    },
    'credentials': {
        'username': {
            'type': 'string',
            'default': None
        },
        'password': {
            'type': 'string',
            'default': None
        }
    },
    'api': {
        'url': {
            'type': 'string',
            'default': ''
        }
    },
    'auth': {
        'url': {
            'type': 'string',
            'default': None
        }
    }
}

RC_OPTION_TO_CLIENT_KWARGS_MAP = {
    'base_url': ['general', 'base_url'],
    'auth_url': ['auth', 'url'],
    'api_url': ['api', 'url'],
    'api_version': ['general', 'api_version'],
    'cacert': ['general', 'cacert'],
    'debug': ['cli', 'debug']
}


class Shell(object):

    def __init__(self):
        # Set up of endpoints is delayed until program is run.
        self.client = None

        # Set up the main parser.
        self.parser = argparse.ArgumentParser(
            description='CLI for Stanley, an automation platform by '
                        'StackStorm. http://stackstorm.com')

        # Set up general program options.
        self.parser.add_argument(
            '--version',
            action='version',
            version='%(prog)s {version}'.format(version=__version__))

        self.parser.add_argument(
            '--url',
            action='store',
            dest='base_url',
            default=None,
            help='Base URL for the API servers. Assumes all servers uses the '
                 'same base URL and default ports are used. Get ST2_BASE_URL'
                 'from the environment variables by default.'
        )

        self.parser.add_argument(
            '--auth-url',
            action='store',
            dest='auth_url',
            default=None,
            help='URL for the autentication service. Get ST2_AUTH_URL'
                 'from the environment variables by default.'
        )

        self.parser.add_argument(
            '--api-url',
            action='store',
            dest='api_url',
            default=None,
            help='URL for the API server. Get ST2_API_URL'
                 'from the environment variables by default.'
        )

        self.parser.add_argument(
            '--api-version',
            action='store',
            dest='api_version',
            default=None,
            help='API version to sue. Get ST2_API_VERSION'
                 'from the environment variables by default.'
        )

        self.parser.add_argument(
            '--cacert',
            action='store',
            dest='cacert',
            default=None,
            help='Path to the CA cert bundle for the SSL endpoints. '
                 'Get ST2_CACERT from the environment variables by default. '
                 'If this is not provided, then SSL cert will not be verified.'
        )

        self.parser.add_argument(
            '--debug',
            action='store_true',
            dest='debug',
            default=False,
            help='Enable debug mode'
        )

        # Set up list of commands and subcommands.
        self.subparsers = self.parser.add_subparsers()
        self.commands = dict()

        self.commands['auth'] = access.TokenCreateCommand(
            models.Token, self, self.subparsers, name='auth')

        self.commands['key'] = datastore.KeyValuePairBranch(
            'Key value pair is used to store commonly used configuration '
            'for reuse in sensors, actions, and rules.',
            self, self.subparsers)

        self.commands['sensor'] = sensor.SensorBranch(
            'An adapter which allows you to integrate Stanley with external system ',
            self, self.subparsers)

        self.commands['trigger'] = trigger.TriggerTypeBranch(
            'An external event that is mapped to a st2 input. It is the '
            'st2 invocation point.',
            self, self.subparsers)

        self.commands['rule'] = resource.ResourceBranch(
            models.Rule,
            'A specification to invoke an "action" on a "trigger" selectively '
            'based on some criteria.',
            self, self.subparsers)

        self.commands['action'] = action.ActionBranch(
            'An activity that happens as a response to the external event.',
            self, self.subparsers)
        self.commands['runner'] = resource.ResourceBranch(
            models.RunnerType,
            'Runner is a type of handler for a specific class of actions.',
            self, self.subparsers, read_only=True)
        self.commands['run'] = action.ActionRunCommand(
            models.Action, self, self.subparsers, name='run', add_help=False)
        self.commands['execution'] = action.ActionExecutionBranch(
            'An invocation of an action.',
            self, self.subparsers)

        self.commands['webhook'] = webhook.WebhookBranch(
            'Webhooks.',
            self, self.subparsers)

    def get_client(self, args, debug=False):
        # Note: Options provided as the CLI argument have the highest precedence
        # Precedence order: cli arguments > environment variables > rc file variables
        cli_options = ['base_url', 'auth_url', 'api_url', 'api_version', 'cacert']
        cli_options = {opt: getattr(args, opt) for opt in cli_options}
        rc_file_options = self._get_rc_file_options()

        kwargs = {}
        kwargs = merge_dicts(kwargs, rc_file_options)
        kwargs = merge_dicts(kwargs, cli_options)
        kwargs['debug'] = debug

        client = Client(**kwargs)

        # If credentials are provided use them and try to authenticate
        rc_config = self._parse_rc_file()

        credentials = rc_config.get('credentials', {})
        username = credentials.get('username', None)
        password = credentials.get('password', None)
        cache_token = rc_config.get('cli', {}).get('cache_token', False)

        if username and password:
            # Credentials are provided, try to authenticate agaist the API
            try:
                token = self._get_auth_token(client=client, username=username, password=password,
                                             cache_token=cache_token)
            except Exception as e:
                print('Failed to authenticate with credentials provided in the config.')
                raise e

            client.token = token
            # TODO: Hack, refactor when splitting out the client
            os.environ['ST2_AUTH_TOKEN'] = token

        return client

    def run(self, argv):
        debug = False
        try:
            # Parse command line arguments.
            args = self.parser.parse_args(args=argv)

            debug = getattr(args, 'debug', False)

            # Set up client.
            self.client = self.get_client(args=args, debug=debug)

            # Execute command.
            args.func(args)

            return 0
        except OperationFailureException as e:
            if debug:
                self._print_debug_info()
            return 2
        except Exception as e:
            # We allow exception to define custom exit codes
            exit_code = getattr(e, 'exit_code', 1)

            print('ERROR: %s\n' % e)
            if debug:
                self._print_debug_info()

            return exit_code

    def _print_debug_info(self):
        # Print client settings
        self._print_client_settings()

        # Print exception traceback
        traceback.print_exc()

    def _print_client_settings(self):
        client = self.client

        if not client:
            return

        rc_file_path = self._get_rc_file_path()

        print('CLI settings:')
        print('----------------')
        print('Config / rc file path: %s' % (rc_file_path))
        print('Client settings:')
        print('----------------')
        print('ST2_BASE_URL: %s' % (client.endpoints['base']))
        print('ST2_AUTH_URL: %s' % (client.endpoints['auth']))
        print('ST2_API_URL: %s' % (client.endpoints['api']))
        print('ST2_AUTH_TOKEN: %s' % (os.environ.get('ST2_AUTH_TOKEN')))
        print('')
        print('Proxy settings:')
        print('---------------')
        print('HTTP_PROXY: %s' % (os.environ.get('HTTP_PROXY', '')))
        print('HTTPS_PROXY: %s' % (os.environ.get('HTTPS_PROXY', '')))
        print('')

    def _get_auth_token(self, client, username, password, cache_token):
        """
        Retrieve a valid auth token.

        If caching is enabled, we will first try to retrieve cached token from a
        file system. If cached token is expired or not available, we will try to
        authenticate using the provided credentials and retrieve a new auth
        token.

        :rtype: ``str``
        """
        if cache_token:
            token = self._get_cached_auth_token(client=client, username=username,
                                                password=password)
        else:
            token = None

        if not token:
            # Token is either expired or not available
            token_obj = self._authenticate_and_retrieve_auth_token(client=client,
                                                                   username=username,
                                                                   password=password)
            self._cache_auth_token(token_obj=token_obj)
            token = token_obj.token

        return token

    def _get_cached_auth_token(self, client, username, password):
        """
        Retrieve cached auth token from the file in the config directory.
        """
        if not os.path.isdir(ST2_CONFIG_DIRECTORY):
            os.makedirs(ST2_CONFIG_DIRECTORY)

        if not os.path.isfile(CACHED_TOKEN_PATH):
            return None

        with open(CACHED_TOKEN_PATH) as fp:
            data = fp.read()

        try:
            data = json.loads(data)

            token = data['token']
            expire_timestamp = data['expire_timestamp']
        except Exception as e:
            msg = 'File with cached token is corrupted: %s' % (str(e))
            raise ValueError(msg)

        now = int(time.time())
        if (expire_timestamp + 15) < now:
            # Token has expired
            return None

        return token

    def _cache_auth_token(self, token_obj):
        """
        Cache auth token in the config directory.

        :param token_obj: Token object.
        :type token_obj: ``object``
        """
        if not os.path.isdir(ST2_CONFIG_DIRECTORY):
            os.makedirs(ST2_CONFIG_DIRECTORY)

        token = token_obj.token
        expire_timestamp = parse_isotime(token_obj.expiry)
        expire_timestamp = calendar.timegm(expire_timestamp.timetuple())

        data = {}
        data['token'] = token
        data['expire_timestamp'] = expire_timestamp
        data = json.dumps(data)

        # Note: We explictly use fdopen instead of open + chmod to avoid a security issue.
        # open + chmod are two operations which means that during a short time frame (between
        # open and chmod) when file can potentially be read by other users if the default
        # permissions used during create allow that.
        fd = os.open(CACHED_TOKEN_PATH, os.O_WRONLY | os.O_CREAT, 0600)
        with os.fdopen(fd, 'w') as fp:
            fp.write(data)

        return True

    def _authenticate_and_retrieve_auth_token(self, client, username, password):
        manager = models.ResourceManager(models.Token, client.endpoints['auth'],
                                         cacert=client.cacert, debug=client.debug)
        instance = models.Token()
        instance = manager.create(instance, auth=(username, password))
        return instance

    def _get_rc_file_path(self):
        path = os.environ.get('ST2_RC_FILE', DEFAULT_RC_FILE_PATH)
        path = os.path.abspath(path)
        return path

    def _parse_rc_file(self):
        rc_file_path = self._get_rc_file_path()

        result = defaultdict(dict)
        if not os.path.isfile(rc_file_path):
            return dict(result)

        config = ConfigParser()

        with open(rc_file_path, 'r') as fp:
            config.readfp(fp)

        for section, keys in six.iteritems(RC_FILE_OPTIONS):
            for key, options in six.iteritems(keys):
                key_type = options['type']
                key_default_value = options['default']

                if config.has_option(section, key):
                    if key_type in ['str', 'string']:
                        get_func = config.get
                    elif key_type in ['int', 'integer']:
                        get_func = config.getint
                    elif key_type in ['float']:
                        get_func = config.getfloat
                    elif key_type in ['bool', 'boolean']:
                        get_func = config.getboolean
                    else:
                        msg = 'Invalid type "%s" for option "%s"' % (key_type, key)
                        raise ValueError(msg)

                    value = get_func(section, key)
                    result[section][key] = value
                else:
                    result[section][key] = key_default_value

        return dict(result)

    def _get_rc_file_options(self):
        rc_options = self._parse_rc_file()

        result = {}
        for kwarg_name, (section, option) in six.iteritems(RC_OPTION_TO_CLIENT_KWARGS_MAP):
            result[kwarg_name] = rc_options.get(section, {}).get(option, None)

        return result


def main(argv=sys.argv[1:]):
    return Shell().run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
