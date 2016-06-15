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
This script submits information which helps StackStorm employees debug different
user problems and issues to StackStorm.

By default the following information is included:

- Logs from /var/log/st2
- StackStorm and mistral config file (/etc/st2/st2.conf, /etc/mistral/mistral.conf)
- All the content (integration packs).
- Information about your system and StackStorm installation (Operating system,
  Python version, StackStorm version, Mistral version)

Note: This script currently assumes it's running on Linux.
"""

import os
import sys
import shutil
import socket
import logging
import tarfile
import argparse
import platform
import tempfile
import httplib

import six
import yaml
import gnupg
import requests
from distutils.spawn import find_executable

import st2common
from st2common.content.utils import get_packs_base_paths
from st2common import __version__ as st2_version
from st2common import config
from st2common.util import date as date_utils
from st2common.util.shell import run_command
from st2debug.constants import GPG_KEY
from st2debug.constants import GPG_KEY_FINGERPRINT
from st2debug.constants import S3_BUCKET_URL
from st2debug.constants import COMPANY_NAME
from st2debug.constants import ARG_NAMES
from st2debug.utils.fs import copy_files
from st2debug.utils.fs import get_full_file_list
from st2debug.utils.fs import get_dirs_in_path
from st2debug.utils.fs import remove_file
from st2debug.utils.fs import remove_dir
from st2debug.utils.system_info import get_cpu_info
from st2debug.utils.system_info import get_memory_info
from st2debug.utils.system_info import get_package_list
from st2debug.utils.git_utils import get_repo_latest_revision_hash
from st2debug.processors import process_st2_config
from st2debug.processors import process_mistral_config
from st2debug.processors import process_content_pack_dir

LOG = logging.getLogger(__name__)

# Constants
GPG_INSTALLED = find_executable('gpg') is not None

LOG_FILE_PATHS = [
    '/var/log/st2/*.log',
    '/var/log/mistral*.log'
]

ST2_CONFIG_FILE_PATH = '/etc/st2/st2.conf'
MISTRAL_CONFIG_FILE_PATH = '/etc/mistral/mistral.conf'

SHELL_COMMANDS = []

# Directory structure inside tarball
DIRECTORY_STRUCTURE = [
    'configs/',
    'logs/',
    'content/',
    'commands/'
]

OUTPUT_PATHS = {
    'logs': 'logs/',
    'configs': 'configs/',
    'content': 'content/',
    'commands': 'commands/',
    'system_info': 'system_info.yaml',
    'user_info': 'user_info.yaml'
}

# Options which should be removed from the st2 config
ST2_CONF_OPTIONS_TO_REMOVE = {
    'database': ['username', 'password'],
    'messaging': ['url']
}

REMOVE_VALUE_NAME = '**removed**'

OUTPUT_FILENAME_TEMPLATE = 'st2-debug-output-%(hostname)s-%(date)s.tar.gz'

DATE_FORMAT = '%Y-%m-%d-%H%M%S'

try:
    config.parse_args(args=[])
except Exception:
    pass


def setup_logging():
    root = LOG
    root.setLevel(logging.INFO)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s  %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)


class DebugInfoCollector(object):
    def __init__(self, include_logs, include_configs, include_content, include_system_info,
                 include_shell_commands=False, user_info=None, debug=False, config_file=None,
                 output_path=None):
        """
        Initialize a DebugInfoCollector object.

        :param include_logs: Include log files in generated archive.
        :type include_logs: ``bool``
        :param include_configs: Include config files in generated archive.
        :type include_configs: ``bool``
        :param include_content: Include pack contents in generated archive.
        :type include_content: ``bool``
        :param include_system_info: Include system information in generated archive.
        :type include_system_info: ``bool``
        :param include_shell_commands: Include shell command output in generated archive.
        :type include_shell_commands: ``bool``
        :param user_info: User info to be included in generated archive.
        :type user_info: ``dict``
        :param debug: Enable debug logging.
        :type debug: ``bool``
        :param config_file: Values from config file to override defaults.
        :type config_file: ``dict``
        :param output_path: Path to write output file to. (optional)
        :type output_path: ``str``
        """
        self.include_logs = include_logs
        self.include_configs = include_configs
        self.include_content = include_content
        self.include_system_info = include_system_info
        self.include_shell_commands = include_shell_commands
        self.user_info = user_info
        self.debug = debug
        self.output_path = output_path

        config_file = config_file or {}
        self.st2_config_file_path = config_file.get('st2_config_file_path', ST2_CONFIG_FILE_PATH)
        self.mistral_config_file_path = config_file.get('mistral_config_file_path',
                                                        MISTRAL_CONFIG_FILE_PATH)
        self.log_file_paths = config_file.get('log_file_paths', LOG_FILE_PATHS[:])
        self.gpg_key = config_file.get('gpg_key', GPG_KEY)
        self.gpg_key_fingerprint = config_file.get('gpg_key_fingerprint', GPG_KEY_FINGERPRINT)
        self.s3_bucket_url = config_file.get('s3_bucket_url', S3_BUCKET_URL)
        self.company_name = config_file.get('company_name', COMPANY_NAME)
        self.shell_commands = config_file.get('shell_commands', SHELL_COMMANDS)

        self.st2_config_file_name = os.path.basename(self.st2_config_file_path)
        self.mistral_config_file_name = os.path.basename(self.mistral_config_file_path)
        self.config_file_paths = [
            self.st2_config_file_path,
            self.mistral_config_file_path
        ]

    def run(self, encrypt=False, upload=False, existing_file=None):
        """
        Run the specified steps.

        :param encrypt: If true, encrypt the archive file.
        :param encrypt: ``bool``
        :param upload: If true, upload the resulting file.
        :param upload: ``bool``
        :param existing_file: Path to an existing archive file. If not specified a new
        archive will be created.
        :param existing_file: ``str``
        """
        temp_files = []

        try:
            if existing_file:
                working_file = existing_file
            else:
                # Create a new archive if an existing file hasn't been provided
                working_file = self.create_archive()
                if not encrypt and not upload:
                    LOG.info('Debug tarball successfully '
                             'generated and can be reviewed at: %s' % working_file)
                else:
                    temp_files.append(working_file)

            if encrypt:
                working_file = self.encrypt_archive(archive_file_path=working_file)
                if not upload:
                    LOG.info('Encrypted debug tarball successfully generated at: %s' %
                             working_file)
                else:
                    temp_files.append(working_file)

            if upload:
                self.upload_archive(archive_file_path=working_file)
                tarball_name = os.path.basename(working_file)
                LOG.info('Debug tarball successfully uploaded to %s (name=%s)' %
                         (self.company_name, tarball_name))
                LOG.info('When communicating with support, please let them know the '
                         'tarball name - %s' % tarball_name)
        finally:
            # Remove temp files
            for temp_file in temp_files:
                assert temp_file.startswith('/tmp')
                remove_file(file_path=temp_file)

    def create_archive(self):
        """
        Create an archive with debugging information.

        :return: Path to the generated archive.
        :rtype: ``str``
        """

        try:
            # 1. Create temporary directory with the final directory structure where we will move
            # files which will be processed and included in the tarball
            self._temp_dir_path = self.create_temp_directories()

            # Prepend temp_dir_path to OUTPUT_PATHS
            output_paths = {}
            for key, path in OUTPUT_PATHS.iteritems():
                output_paths[key] = os.path.join(self._temp_dir_path, path)

            # 2. Moves all the files to the temporary directory
            LOG.info('Collecting files...')
            if self.include_logs:
                self.collect_logs(output_paths['logs'])
            if self.include_configs:
                self.collect_config_files(output_paths['configs'])
            if self.include_content:
                self.collect_pack_content(output_paths['content'])
            if self.include_system_info:
                self.add_system_information(output_paths['system_info'])
            if self.user_info:
                self.add_user_info(output_paths['user_info'])
            if self.include_shell_commands:
                self.add_shell_command_output(output_paths['commands'])

            # 3. Create a tarball
            return self.create_tarball(self._temp_dir_path)

        except Exception as e:
            LOG.exception('Failed to generate tarball', exc_info=True)
            raise e

        finally:
            # Ensure temp files are removed regardless of success or failure
            assert self._temp_dir_path.startswith('/tmp')
            remove_dir(self._temp_dir_path)

    def encrypt_archive(self, archive_file_path):
        """
        Encrypt archive with debugging information using our public key.

        :param archive_file_path: Path to the non-encrypted tarball file.
        :type archive_file_path: ``str``

        :return: Path to the encrypted archive.
        :rtype: ``str``
        """
        try:
            assert archive_file_path.endswith('.tar.gz')

            LOG.info('Encrypting tarball...')
            gpg = gnupg.GPG(verbose=self.debug)

            # Import our public key
            import_result = gpg.import_keys(self.gpg_key)
            # pylint: disable=no-member
            assert import_result.count == 1

            encrypted_archive_output_file_name = os.path.basename(archive_file_path) + '.asc'
            encrypted_archive_output_file_path = os.path.join('/tmp',
                                                              encrypted_archive_output_file_name)
            with open(archive_file_path, 'rb') as fp:
                gpg.encrypt_file(file=fp,
                                 recipients=self.gpg_key_fingerprint,
                                 always_trust=True,
                                 output=encrypted_archive_output_file_path)
            return encrypted_archive_output_file_path
        except Exception as e:
            LOG.exception('Failed to encrypt archive', exc_info=True)
            raise e

    def upload_archive(self, archive_file_path):
        """
        Upload the encrypted archive.

        :param archive_file_path: Path to the encrypted tarball file.
        :type archive_file_path: ``str``
        """
        try:
            assert archive_file_path.endswith('.asc')

            LOG.debug('Uploading tarball...')
            file_name = os.path.basename(archive_file_path)
            url = self.s3_bucket_url + file_name
            assert url.startswith('https://')

            with open(archive_file_path, 'rb') as fp:
                response = requests.put(url=url, files={'file': fp})
            assert response.status_code == httplib.OK
        except Exception as e:
            LOG.exception('Failed to upload tarball to %s' % self.company_name, exc_info=True)
            raise e

    def collect_logs(self, output_path):
        """
        Copy log files to the output path.

        :param output_path: Path where log files will be copied to.
        :type output_path: ``str``
        """
        LOG.debug('Including log files')
        for file_path_glob in self.log_file_paths:
            log_file_list = get_full_file_list(file_path_glob=file_path_glob)
            copy_files(file_paths=log_file_list, destination=output_path)

    def collect_config_files(self, output_path):
        """
        Copy config files to the output path.

        :param output_path: Path where config files will be copied to.
        :type output_path: ``str``
        """
        LOG.debug('Including config files')
        copy_files(file_paths=self.config_file_paths, destination=output_path)

        st2_config_path = os.path.join(output_path, self.st2_config_file_name)
        process_st2_config(config_path=st2_config_path)

        mistral_config_path = os.path.join(output_path, self.mistral_config_file_name)
        process_mistral_config(config_path=mistral_config_path)

    @staticmethod
    def collect_pack_content(output_path):
        """
        Copy pack contents to the output path.

        :param output_path: Path where pack contents will be copied to.
        :type output_path: ``str``
        """
        LOG.debug('Including content')

        packs_base_paths = get_packs_base_paths()
        for index, packs_base_path in enumerate(packs_base_paths, 1):
            dst = os.path.join(output_path, 'dir-%s' % index)

            try:
                shutil.copytree(src=packs_base_path, dst=dst)
            except IOError:
                continue

        base_pack_dirs = get_dirs_in_path(file_path=output_path)

        for base_pack_dir in base_pack_dirs:
            pack_dirs = get_dirs_in_path(file_path=base_pack_dir)

            for pack_dir in pack_dirs:
                process_content_pack_dir(pack_dir=pack_dir)

    def add_system_information(self, output_path):
        """
        Collect and write system information to output path.

        :param output_path: Path where system information will be written to.
        :type output_path: ``str``
        """
        LOG.debug('Including system info')

        system_information = yaml.dump(self.get_system_information(),
                                       default_flow_style=False)

        with open(output_path, 'w') as fp:
            fp.write(system_information)

    def add_user_info(self, output_path):
        """
        Write user info to output path as YAML.

        :param output_path: Path where user info will be written.
        :type output_path: ``str``
        """
        LOG.debug('Including user info')
        user_info = yaml.dump(self.user_info, default_flow_style=False)

        with open(output_path, 'w') as fp:
            fp.write(user_info)

    def add_shell_command_output(self, output_path):
        """"
        Get output of the required shell command and redirect the output to output path.

        :param output_path: Directory where output files will be written
        :param output_path: ``str``
        """
        LOG.debug('Including the required shell commands output files')
        for cmd in self.shell_commands:
            output_file = os.path.join(output_path, '%s.txt' % self.format_output_filename(cmd))
            exit_code, stdout, stderr = run_command(cmd=cmd, shell=True)
            with open(output_file, 'w') as fp:
                fp.write('[BEGIN STDOUT]\n')
                fp.write(stdout)
                fp.write('[END STDOUT]\n')
                fp.write('[BEGIN STDERR]\n')
                fp.write(stderr)
                fp.write('[END STDERR]')

    def create_tarball(self, temp_dir_path):
        """
        Create tarball with the contents of temp_dir_path.

        Tarball will be written to self.output_path, if set. Otherwise it will
        be written to /tmp a name generated according to OUTPUT_FILENAME_TEMPLATE.

        :param temp_dir_path: Base directory to include in tarbal.
        :type temp_dir_path: ``str``

        :return: Path to the created tarball.
        :rtype: ``str``
        """
        LOG.info('Creating tarball...')
        if self.output_path:
            output_file_path = self.output_path
        else:
            date = date_utils.get_datetime_utc_now().strftime(DATE_FORMAT)
            values = {'hostname': socket.gethostname(), 'date': date}

            output_file_name = OUTPUT_FILENAME_TEMPLATE % values
            output_file_path = os.path.join('/tmp', output_file_name)

        with tarfile.open(output_file_path, 'w:gz') as tar:
            tar.add(temp_dir_path, arcname='')

        return output_file_path

    @staticmethod
    def create_temp_directories():
        """
        Creates a new temp directory and creates the directory structure as defined
        by DIRECTORY_STRUCTURE.

        :return: Path to temp directory.
        :rtype: ``str``
        """
        temp_dir_path = tempfile.mkdtemp()

        for directory_name in DIRECTORY_STRUCTURE:
            full_path = os.path.join(temp_dir_path, directory_name)
            os.mkdir(full_path)

        return temp_dir_path

    @staticmethod
    def format_output_filename(cmd):
        """"
        Remove whitespace and special characters from a shell command.

        Used to create filename-safe representations of a shell command.

        :param cmd: Shell command.
        :type cmd: ``str``
        :return: Formatted filename.
        :rtype: ``str``
        """
        return cmd.translate(None, """ !@#$%^&*()[]{};:,./<>?\|`~=+"'""")

    @staticmethod
    def get_system_information():
        """
        Retrieve system information which is included in the report.

        :rtype: ``dict``
        """
        system_information = {
            'hostname': socket.gethostname(),
            'operating_system': {},
            'hardware': {
                'cpu': {},
                'memory': {}
            },
            'python': {},
            'stackstorm': {},
            'mistral': {}
        }

        # Operating system information
        system_information['operating_system']['system'] = platform.system()
        system_information['operating_system']['release'] = platform.release()
        system_information['operating_system']['operating_system'] = platform.platform()
        system_information['operating_system']['platform'] = platform.system()
        system_information['operating_system']['architecture'] = ' '.join(platform.architecture())

        if platform.system().lower() == 'linux':
            distribution = ' '.join(platform.linux_distribution())
            system_information['operating_system']['distribution'] = distribution

        system_information['python']['version'] = sys.version.split('\n')[0]

        # Hardware information
        cpu_info = get_cpu_info()

        if cpu_info:
            core_count = len(cpu_info)
            model = cpu_info[0]['model_name']
            system_information['hardware']['cpu'] = {
                'core_count': core_count,
                'model_name': model
            }
        else:
            # Unsupported platform
            system_information['hardware']['cpu'] = 'unsupported platform'

        memory_info = get_memory_info()

        if memory_info:
            total = memory_info['MemTotal'] / 1024
            free = memory_info['MemFree'] / 1024
            used = (total - free)
            system_information['hardware']['memory'] = {
                'total': total,
                'used': used,
                'free': free
            }
        else:
            # Unsupported platform
            system_information['hardware']['memory'] = 'unsupported platform'

        # StackStorm information
        system_information['stackstorm']['version'] = st2_version

        st2common_path = st2common.__file__
        st2common_path = os.path.dirname(st2common_path)

        if 'st2common/st2common' in st2common_path:
            # Assume we are running source install
            base_install_path = st2common_path.replace('/st2common/st2common', '')

            revision_hash = get_repo_latest_revision_hash(repo_path=base_install_path)

            system_information['stackstorm']['installation_method'] = 'source'
            system_information['stackstorm']['revision_hash'] = revision_hash
        else:
            package_list = get_package_list(name_startswith='st2')

            system_information['stackstorm']['installation_method'] = 'package'
            system_information['stackstorm']['packages'] = package_list

        # Mistral information
        repo_path = '/opt/openstack/mistral'
        revision_hash = get_repo_latest_revision_hash(repo_path=repo_path)
        system_information['mistral']['installation_method'] = 'source'
        system_information['mistral']['revision_hash'] = revision_hash

        return system_information


def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--exclude-logs', action='store_true', default=False,
                        help='Don\'t include logs in the generated tarball')
    parser.add_argument('--exclude-configs', action='store_true', default=False,
                        help='Don\'t include configs in the generated tarball')
    parser.add_argument('--exclude-content', action='store_true', default=False,
                        help='Don\'t include content packs in the generated tarball')
    parser.add_argument('--exclude-system-info', action='store_true', default=False,
                        help='Don\'t include system information in the generated tarball')
    parser.add_argument('--exclude-shell-commands', action='store_true', default=False,
                        help='Don\'t include shell commands output in the generated tarball')
    parser.add_argument('--yes', action='store_true', default=False,
                        help='Run in non-interactive mode and answer "yes" to all the questions')
    parser.add_argument('--review', action='store_true', default=False,
                        help='Generate the tarball, but don\'t encrypt and upload it')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='Enable debug mode')
    parser.add_argument('--config', action='store', default=None,
                        help='Get required configurations from config file')
    parser.add_argument('--output', action='store', default=None,
                        help='Specify output file path')
    parser.add_argument('--existing-file', action='store', default=None,
                        help='Specify an existing file to operate on')
    args = parser.parse_args()

    setup_logging()

    # Ensure that not all options have been excluded
    abort = True
    for arg_name in ARG_NAMES:
        abort &= getattr(args, arg_name, False)

    if abort:
        print('Generated tarball would be empty. Aborting.')
        sys.exit(2)

    # Get setting overrides from yaml file if specified
    if args.config:
        try:
            with open(args.config, 'r') as yaml_file:
                config_file = yaml.safe_load(yaml_file)
        except Exception as e:
            LOG.error('Failed to parse config file: %s' % e)
            sys.exit(1)

        if not isinstance(config_file, dict):
            LOG.error('Unrecognized config file format')
            sys.exit(1)
    else:
        config_file = {}

    company_name = config_file.get('company_name', COMPANY_NAME)

    # Defaults
    encrypt = True
    upload = True

    if args.review:
        encrypt = False
        upload = False

    if encrypt:
        # When not running in review mode, GPG needs to be installed and
        # available
        if not GPG_INSTALLED:
            msg = ('"gpg" binary not found, can\'t proceed. Make sure "gpg" is installed '
                   'and available in PATH.')
            raise ValueError(msg)

    if not args.yes and not args.existing_file and upload:
        submitted_content = [name.replace('exclude_', '') for name in ARG_NAMES if
                             not getattr(args, name, False)]
        submitted_content = ', '.join(submitted_content)
        print('This will submit the following information to %s: %s' % (company_name,
                                                                        submitted_content))
        value = six.moves.input('Are you sure you want to proceed? [y/n] ')
        if value.strip().lower() not in ['y', 'yes']:
            print('Aborting')
            sys.exit(1)

    # Prompt user for optional additional context info
    user_info = {}
    if not args.yes and not args.existing_file:
        print('If you want us to get back to you via email, you can provide additional context '
              'such as your name, email and an optional comment')
        value = six.moves.input('Would you like to provide additional context? [y/n] ')
        if value.strip().lower() in ['y', 'yes']:
            user_info['name'] = six.moves.input('Name: ')
            user_info['email'] = six.moves.input('Email: ')
            user_info['comment'] = six.moves.input('Comment: ')

    debug_collector = DebugInfoCollector(include_logs=not args.exclude_logs,
                                         include_configs=not args.exclude_configs,
                                         include_content=not args.exclude_content,
                                         include_system_info=not args.exclude_system_info,
                                         include_shell_commands=not args.exclude_shell_commands,
                                         user_info=user_info,
                                         debug=args.debug,
                                         config_file=config_file,
                                         output_path=args.output)

    debug_collector.run(encrypt=encrypt, upload=upload, existing_file=args.existing_file)
