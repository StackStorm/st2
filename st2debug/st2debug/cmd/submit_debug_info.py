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
from st2debug.constants import GPG_KEY
from st2debug.constants import GPG_KEY_FINGERPRINT
from st2debug.constants import S3_BUCKET_URL
from st2debug.utils.fs import copy_files
from st2debug.utils.fs import get_full_file_list
from st2debug.utils.fs import get_dirs_in_path
from st2debug.utils.fs import remove_file
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

ST2_LOG_FILES_PATH = '/var/log/st2/*.log'
MISTRAL_LOG_FILES_PATH = '/var/log/mistral*.log'

LOG_FILE_PATHS = [
    ST2_LOG_FILES_PATH,
    MISTRAL_LOG_FILES_PATH
]

ST2_CONFIG_FILE_PATH = '/etc/st2/st2.conf'
MISTRAL_CONFIG_FILE_PATH = '/etc/mistral/mistral.conf'

ST2_CONFIG_FILE_NAME = os.path.split(ST2_CONFIG_FILE_PATH)[1]
MISTRAL_CONFIG_FILE_NAME = os.path.split(MISTRAL_CONFIG_FILE_PATH)[1]

CONFIG_FILE_PATHS = [
    ST2_CONFIG_FILE_PATH,
    MISTRAL_CONFIG_FILE_PATH
]

# Directory structure inside tarball
DIRECTORY_STRUCTURE = [
    'configs/',
    'logs/',
    'content/'
]

# Options which should be removed from the st2 config
ST2_CONF_OPTIONS_TO_REMOVE = {
    'database': ['username', 'password'],
    'messaging': ['url']
}

REMOVE_VALUE_NAME = '**removed**'

OUTPUT_FILENAME_TEMPLATE = 'st2-debug-output-%(hostname)s-%(date)s.tar.gz'

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


def create_archive(include_logs, include_configs, include_content, include_system_info,
                   user_info=None, debug=False):
    """
    Create an archive with debugging information.

    :return: Path to the generated archive.
    :rtype: ``str``
    """
    date = date_utils.get_datetime_utc_now().strftime('%Y-%m-%d-%H:%M:%S')
    values = {'hostname': socket.gethostname(), 'date': date}

    output_file_name = OUTPUT_FILENAME_TEMPLATE % values
    output_file_path = os.path.join('/tmp', output_file_name)

    # 1. Create temporary directory with the final directory structure where we will move files
    # which will be processed and included in the tarball
    temp_dir_path = tempfile.mkdtemp()

    output_paths = {
        'logs': os.path.join(temp_dir_path, 'logs/'),
        'configs': os.path.join(temp_dir_path, 'configs/'),
        'content': os.path.join(temp_dir_path, 'content/'),
        'system_info': os.path.join(temp_dir_path, 'system_info.yaml'),
        'user_info': os.path.join(temp_dir_path, 'user_info.yaml')
    }

    for directory_name in DIRECTORY_STRUCTURE:
        full_path = os.path.join(temp_dir_path, directory_name)
        os.mkdir(full_path)

    # 2. Moves all the files to the temporary directory
    LOG.info('Collecting files...')

    # Logs
    if include_logs:
        LOG.debug('Including log files')

        for file_path_glob in LOG_FILE_PATHS:
            log_file_list = get_full_file_list(file_path_glob=file_path_glob)
            copy_files(file_paths=log_file_list, destination=output_paths['logs'])

    # Config files
    if include_configs:
        LOG.debug('Including config files')
        copy_files(file_paths=CONFIG_FILE_PATHS, destination=output_paths['configs'])

    # Content
    if include_content:
        LOG.debug('Including content')

        packs_base_paths = get_packs_base_paths()
        for index, packs_base_path in enumerate(packs_base_paths, 1):
            dst = os.path.join(output_paths['content'], 'dir-%s' % (index))

            try:
                shutil.copytree(src=packs_base_path, dst=dst)
            except IOError:
                continue

    # System information
    if include_system_info:
        LOG.debug('Including system info')

        system_information = get_system_information()
        system_information = yaml.dump(system_information, default_flow_style=False)

        with open(output_paths['system_info'], 'w') as fp:
            fp.write(system_information)

    if user_info:
        LOG.debug('Including user info')
        user_info = yaml.dump(user_info, default_flow_style=False)

        with open(output_paths['user_info'], 'w') as fp:
            fp.write(user_info)

    # Configs
    st2_config_path = os.path.join(output_paths['configs'], ST2_CONFIG_FILE_NAME)
    process_st2_config(config_path=st2_config_path)

    mistral_config_path = os.path.join(output_paths['configs'], MISTRAL_CONFIG_FILE_NAME)
    process_mistral_config(config_path=mistral_config_path)

    # Content
    base_pack_dirs = get_dirs_in_path(file_path=output_paths['content'])

    for base_pack_dir in base_pack_dirs:
        pack_dirs = get_dirs_in_path(file_path=base_pack_dir)

        for pack_dir in pack_dirs:
            process_content_pack_dir(pack_dir=pack_dir)

    # 4. Create a tarball
    LOG.info('Creating tarball...')

    with tarfile.open(output_file_path, 'w:gz') as tar:
        for file_path in output_paths.values():
            file_path = os.path.normpath(file_path)
            source_dir = file_path

            if not os.path.exists(source_dir):
                continue

            if '.' in file_path:
                arcname = os.path.basename(file_path)
            else:
                arcname = os.path.split(file_path)[-1]

            tar.add(source_dir, arcname=arcname)

    return output_file_path


def encrypt_archive(archive_file_path, debug=False):
    """
    Encrypt archive with debugging information using our public key.

    :param archive_file_path: Path to the non-encrypted tarball file.
    :type archive_file_path: ``str``

    :return: Path to the encrypted archive.
    :rtype: ``str``
    """
    assert archive_file_path.endswith('.tar.gz')

    LOG.info('Encrypting tarball...')
    gpg = gnupg.GPG(verbose=debug)

    # Import our public key
    import_result = gpg.import_keys(GPG_KEY)
    # pylint: disable=no-member
    assert import_result.count == 1

    encrypted_archive_output_file_path = archive_file_path + '.asc'
    with open(archive_file_path, 'rb') as fp:
        gpg.encrypt_file(fp,
                         recipients=GPG_KEY_FINGERPRINT,
                         always_trust=True,
                         output=encrypted_archive_output_file_path)

    return encrypted_archive_output_file_path


def upload_archive(archive_file_path):
    assert archive_file_path.endswith('.asc')

    LOG.debug('Uploading tarball...')
    files = {'file': open(archive_file_path, 'rb')}
    file_name = os.path.split(archive_file_path)[1]
    url = S3_BUCKET_URL + file_name
    assert url.startswith('https://')

    response = requests.put(url=url, files=files)
    assert response.status_code == httplib.OK


def create_and_review_archive(include_logs, include_configs, include_content, include_system_info,
                              user_info=None, debug=False):
    try:
        plain_text_output_path = create_archive(include_logs=include_logs,
                                                include_configs=include_configs,
                                                include_content=include_content,
                                                include_system_info=include_system_info,
                                                user_info=user_info,
                                                debug=debug)
    except Exception:
        LOG.exception('Failed to generate tarball', exc_info=True)
    else:
        LOG.info('Debug tarball successfully generated and can be reviewed at: %s' %
                 (plain_text_output_path))


def create_and_upload_archive(include_logs, include_configs, include_content, include_system_info,
                              user_info=None, debug=False):
    try:
        plain_text_output_path = create_archive(include_logs=include_logs,
                                                include_configs=include_configs,
                                                include_content=include_content,
                                                include_system_info=include_system_info,
                                                user_info=user_info,
                                                debug=debug)
        encrypted_output_path = encrypt_archive(archive_file_path=plain_text_output_path)
        upload_archive(archive_file_path=encrypted_output_path)
    except Exception:
        LOG.exception('Failed to upload tarball to StackStorm', exc_info=True)
        plain_text_output_path = None
        encrypted_output_path = None
    else:
        tarball_name = os.path.basename(encrypted_output_path)
        LOG.info('Debug tarball successfully uploaded to StackStorm (name=%s)' % (tarball_name))
        LOG.info('When communicating with support, please let them know the tarball name - %s' %
                 (tarball_name))

    finally:
        # Remove tarballs
        if plain_text_output_path:
            assert plain_text_output_path.startswith('/tmp')
            remove_file(file_path=plain_text_output_path)
        if encrypted_output_path:
            assert encrypted_output_path.startswith('/tmp')
            remove_file(file_path=encrypted_output_path)


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
    parser.add_argument('--yes', action='store_true', default=False,
                        help='Run in non-interative mode and answer "yes" to all the questions')
    parser.add_argument('--review', action='store_true', default=False,
                        help='Generate the tarball, but don\'t encrypt and upload it')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='Enable debug mode')
    args = parser.parse_args()

    arg_names = ['exclude_logs', 'exclude_configs', 'exclude_content',
                 'exclude_system_info']

    abort = True
    for arg_name in arg_names:
        value = getattr(args, arg_name, False)
        abort &= value

    if abort:
        print('Generated tarball would be empty. Aborting.')
        sys.exit(2)

    submited_content = [name.replace('exclude_', '') for name in arg_names if
                        not getattr(args, name, False)]
    submited_content = ', '.join(submited_content)

    if not args.yes and not args.review:
        # When not running in review mode, GPG needs to be installed and
        # available
        if not GPG_INSTALLED:
            msg = ('"gpg" binary not found, can\'t proceed. Make sure "gpg" is installed '
                   'and available in PATH.')
            raise ValueError(msg)

        print('This will submit the following information to StackStorm: %s' % (submited_content))
        value = six.moves.input('Are you sure you want to proceed? [y/n] ')
        if value.strip().lower() not in ['y', 'yes']:
            print('Aborting')
            sys.exit(1)

    # Prompt user for optional additional context info
    user_info = {}

    print('If you want us to get back to you via email, you can provide additional context '
          'such as your name, email and an optional comment')
    value = six.moves.input('Would you like to provide additional context? [y/n] ')
    if value.strip().lower() in ['y', 'yes']:
        user_info['name'] = six.moves.input('Name: ')
        user_info['email'] = six.moves.input('Email: ')
        user_info['comment'] = six.moves.input('Comment: ')
    else:
        user_info = {}

    setup_logging()

    if args.review:
        create_and_review_archive(include_logs=not args.exclude_logs,
                                  include_configs=not args.exclude_configs,
                                  include_content=not args.exclude_content,
                                  include_system_info=not args.exclude_system_info,
                                  user_info=user_info,
                                  debug=args.debug)
    else:
        create_and_upload_archive(include_logs=not args.exclude_logs,
                                  include_configs=not args.exclude_configs,
                                  include_content=not args.exclude_content,
                                  include_system_info=not args.exclude_system_info,
                                  user_info=user_info,
                                  debug=args.debug)
