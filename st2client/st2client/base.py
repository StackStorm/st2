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
import json
import logging
import time
import calendar
import traceback

import six
import requests

from st2client import models
from st2client.config_parser import CLIConfigParser
from st2client.config_parser import ST2_CONFIG_DIRECTORY
from st2client.config_parser import ST2_CONFIG_PATH
from st2client.client import Client
from st2client.config import get_config
from st2client.utils.date import parse as parse_isotime
from st2client.utils.misc import merge_dicts

__all__ = [
    'BaseCLIApp'
]

# How many seconds before the token actual expiration date we should consider the token as
# expired. This is used to prevent the operation from failing durig the API request because the
# token was just about to expire.
TOKEN_EXPIRATION_GRACE_PERIOD_SECONDS = 15

CONFIG_OPTION_TO_CLIENT_KWARGS_MAP = {
    'base_url': ['general', 'base_url'],
    'auth_url': ['auth', 'url'],
    'api_url': ['api', 'url'],
    'api_version': ['general', 'api_version'],
    'api_key': ['credentials', 'api_key'],
    'cacert': ['general', 'cacert'],
    'debug': ['cli', 'debug']
}


class BaseCLIApp(object):
    """
    Base class for StackStorm CLI apps.
    """

    LOG = logging.getLogger(__name__)  # logger instance to use
    client = None  # st2client instance

    # A list of command classes for which automatic authentication should be skipped.
    SKIP_AUTH_CLASSES = []

    def get_client(self, args, debug=False):
        ST2_CLI_SKIP_CONFIG = os.environ.get('ST2_CLI_SKIP_CONFIG', 0)
        ST2_CLI_SKIP_CONFIG = int(ST2_CLI_SKIP_CONFIG)

        skip_config = args.skip_config
        skip_config = skip_config or ST2_CLI_SKIP_CONFIG

        # Note: Options provided as the CLI argument have the highest precedence
        # Precedence order: cli arguments > environment variables > rc file variables
        cli_options = ['base_url', 'auth_url', 'api_url', 'api_version', 'cacert']
        cli_options = {opt: getattr(args, opt, None) for opt in cli_options}
        config_file_options = self._get_config_file_options(args=args)

        kwargs = {}

        if not skip_config:
            # Config parsing is not skipped
            kwargs = merge_dicts(kwargs, config_file_options)

        kwargs = merge_dicts(kwargs, cli_options)
        kwargs['debug'] = debug

        client = Client(**kwargs)

        if skip_config:
            # Config parsing is skipped
            self.LOG.info('Skipping parsing CLI config')
            return client

        # Ok to use config at this point
        rc_config = get_config()

        # Silence SSL warnings
        silence_ssl_warnings = rc_config.get('general', {}).get('silence_ssl_warnings', False)
        if silence_ssl_warnings:
            requests.packages.urllib3.disable_warnings()

        # We skip automatic authentication for some commands such as auth
        try:
            command_class_name = args.func.im_class.__name__
        except Exception:
            command_class_name = None

        if command_class_name in self.SKIP_AUTH_CLASSES:
            return client

        # We also skip automatic authentication if token is provided via the environment variable
        # or as a command line argument
        env_var_token = os.environ.get('ST2_AUTH_TOKEN', None)
        cli_argument_token = getattr(args, 'token', None)
        env_var_api_key = os.environ.get('ST2_API_KEY', None)
        cli_argument_api_key = getattr(args, 'api_key', None)
        if env_var_token or cli_argument_token or env_var_api_key or cli_argument_api_key:
            return client

        # If credentials are provided in the CLI config use them and try to authenticate
        credentials = rc_config.get('credentials', {})
        username = credentials.get('username', None)
        password = credentials.get('password', None)
        cache_token = rc_config.get('cli', {}).get('cache_token', False)

        if username:
            # Credentials are provided, try to authenticate agaist the API
            try:
                token = self._get_auth_token(client=client, username=username, password=password,
                                             cache_token=cache_token)
            except requests.exceptions.ConnectionError as e:
                self.LOG.warn('Auth API server is not available, skipping authentication.')
                self.LOG.exception(e)
                return client
            except Exception as e:
                print('Failed to authenticate with credentials provided in the config.')
                raise e
            client.token = token
            # TODO: Hack, refactor when splitting out the client
            os.environ['ST2_AUTH_TOKEN'] = token

        return client

    def _get_config_file_options(self, args):
        """
        Parse the config and return kwargs which can be passed to the Client
        constructor.

        :rtype: ``dict``
        """
        rc_options = self._parse_config_file(args=args)
        result = {}
        for kwarg_name, (section, option) in six.iteritems(CONFIG_OPTION_TO_CLIENT_KWARGS_MAP):
            result[kwarg_name] = rc_options.get(section, {}).get(option, None)

        return result

    def _parse_config_file(self, args):
        config_file_path = self._get_config_file_path(args=args)

        parser = CLIConfigParser(config_file_path=config_file_path, validate_config_exists=False)
        result = parser.parse()
        return result

    def _get_config_file_path(self, args):
        """
        Retrieve path to the CLI configuration file.

        :rtype: ``str``
        """
        path = os.environ.get('ST2_CONFIG_FILE', ST2_CONFIG_PATH)

        if args.config_file:
            path = args.config_file

        path = os.path.abspath(os.path.expanduser(path))
        if path != ST2_CONFIG_PATH and not os.path.isfile(path):
            raise ValueError('Config "%s" not found' % (path))

        return path

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

        :rtype: ``str``
        """
        if not os.path.isdir(ST2_CONFIG_DIRECTORY):
            os.makedirs(ST2_CONFIG_DIRECTORY)

        cached_token_path = self._get_cached_token_path_for_user(username=username)

        if not os.access(ST2_CONFIG_DIRECTORY, os.R_OK):
            # We don't have read access to the file with a cached token
            message = ('Unable to retrieve cached token from "%s" (user %s doesn\'t have read '
                       'access to the parent directory). Subsequent requests won\'t use a '
                       'cached token meaning they may be slower.' % (cached_token_path,
                                                                     os.getlogin()))
            self.LOG.warn(message)
            return None

        if not os.path.isfile(cached_token_path):
            return None

        if not os.access(cached_token_path, os.R_OK):
            # We don't have read access to the file with a cached token
            message = ('Unable to retrieve cached token from "%s" (user %s doesn\'t have read '
                       'access to this file). Subsequent requests won\'t use a cached token '
                       'meaning they may be slower.' % (cached_token_path, os.getlogin()))
            self.LOG.warn(message)
            return None

        # Safety check for too permissive permissions
        file_st_mode = oct(os.stat(cached_token_path).st_mode & 0777)
        others_st_mode = int(file_st_mode[-1])

        if others_st_mode >= 4:
            # Every user has access to this file which is dangerous
            message = ('Permissions (%s) for cached token file "%s" are to permissive. Please '
                       'restrict the permissions and make sure only your own user can read '
                       'from the file' % (file_st_mode, cached_token_path))
            self.LOG.warn(message)

        with open(cached_token_path) as fp:
            data = fp.read()

        try:
            data = json.loads(data)

            token = data['token']
            expire_timestamp = data['expire_timestamp']
        except Exception as e:
            msg = ('File "%s" with cached token is corrupted or invalid (%s). Please delete '
                   ' this file' % (cached_token_path, str(e)))
            raise ValueError(msg)

        now = int(time.time())
        if (expire_timestamp - TOKEN_EXPIRATION_GRACE_PERIOD_SECONDS) < now:
            self.LOG.debug('Cached token from file "%s" has expired' % (cached_token_path))
            # Token has expired
            return None

        self.LOG.debug('Using cached token from file "%s"' % (cached_token_path))
        return token

    def _cache_auth_token(self, token_obj):
        """
        Cache auth token in the config directory.

        :param token_obj: Token object.
        :type token_obj: ``object``
        """
        if not os.path.isdir(ST2_CONFIG_DIRECTORY):
            os.makedirs(ST2_CONFIG_DIRECTORY)

        username = token_obj.user
        cached_token_path = self._get_cached_token_path_for_user(username=username)

        if not os.access(ST2_CONFIG_DIRECTORY, os.W_OK):
            # We don't have write access to the file with a cached token
            message = ('Unable to write token to "%s" (user %s doesn\'t have write '
                       'access to the parent directory). Subsequent requests won\'t use a '
                       'cached token meaning they may be slower.' % (cached_token_path,
                                                                     os.getlogin()))
            self.LOG.warn(message)
            return None

        if os.path.isfile(cached_token_path) and not os.access(cached_token_path, os.W_OK):
            # We don't have write access to the file with a cached token
            message = ('Unable to write token to "%s" (user %s doesn\'t have write '
                       'access to this file). Subsequent requests won\'t use a '
                       'cached token meaning they may be slower.' % (cached_token_path,
                                                                     os.getlogin()))
            self.LOG.warn(message)
            return None

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
        fd = os.open(cached_token_path, os.O_WRONLY | os.O_CREAT, 0600)
        with os.fdopen(fd, 'w') as fp:
            fp.write(data)

        self.LOG.debug('Token has been cached in "%s"' % (cached_token_path))
        return True

    def _authenticate_and_retrieve_auth_token(self, client, username, password):
        manager = models.ResourceManager(models.Token, client.endpoints['auth'],
                                         cacert=client.cacert, debug=client.debug)
        instance = models.Token()
        instance = manager.create(instance, auth=(username, password))
        return instance

    def _get_cached_token_path_for_user(self, username):
        """
        Retrieve cached token path for the provided username.
        """
        file_name = 'token-%s' % (username)
        result = os.path.abspath(os.path.join(ST2_CONFIG_DIRECTORY, file_name))
        return result

    def _print_config(self, args):
        config = self._parse_config_file(args=args)

        for section, options in six.iteritems(config):
            print('[%s]' % (section))

            for name, value in six.iteritems(options):
                print('%s = %s' % (name, value))

    def _print_debug_info(self, args):
        # Print client settings
        self._print_client_settings(args=args)

        # Print exception traceback
        traceback.print_exc()

    def _print_client_settings(self, args):
        client = self.client

        if not client:
            return

        config_file_path = self._get_config_file_path(args=args)

        print('CLI settings:')
        print('----------------')
        print('Config file path: %s' % (config_file_path))
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
