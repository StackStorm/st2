# -*- coding: utf-8 -*-
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
Module containing pack download and install related functions.
"""

from __future__ import absolute_import

import os
import shutil
import hashlib
import stat
import re

from git.repo import Repo
from gitdb.exc import BadName, BadObject
from lockfile import LockFile

from st2common import log as logging
from st2common.content import utils
from st2common.constants.pack import MANIFEST_FILE_NAME
from st2common.constants.pack import PACK_RESERVED_CHARACTERS
from st2common.constants.pack import PACK_VERSION_SEPARATOR
from st2common.constants.pack import PACK_VERSION_REGEX
from st2common.services.packs import get_pack_from_index
from st2common.util.pack import get_pack_metadata
from st2common.util.pack import get_pack_ref_from_metadata
from st2common.util.green import shell
from st2common.util.versioning import complex_semver_match
from st2common.util.versioning import get_stackstorm_version

__all__ = [
    'download_pack',

    'get_repo_url',
    'eval_repo_url'
]

LOG = logging.getLogger(__name__)

CONFIG_FILE = 'config.yaml'
CURRENT_STACKSTROM_VERSION = get_stackstorm_version()


def download_pack(pack, abs_repo_base='/opt/stackstorm/packs', verify_ssl=True, force=False,
                  proxy_config=None, force_permissions=True, logger=LOG):
    """
    Download the pack and move it to /opt/stackstorm/packs.

    :param abs_repo_base: Path where the pack should be installed to.
    :type abs_repo_base: ``str``

    :param pack: Pack name.
    :rtype pack: ``str``

    :param force_permissions: True to force 770 permission on all the pack content.
    :type force_permissions: ``bool``

    :param force: Force the installation and ignore / delete the lock file if it already exists.
    :type force: ``bool``

    :return: (pack_url, pack_ref, result)
    :rtype: tuple
    """
    proxy_config = proxy_config or {}

    try:
        pack_url, pack_version = get_repo_url(pack, proxy_config=proxy_config)
    except Exception as e:
        # Pack not found or similar
        result = [None, pack, (False, str(e))]
        return result

    result = [pack_url, None, None]

    temp_dir_name = hashlib.md5(pack_url).hexdigest()
    lock_file = LockFile('/tmp/%s' % (temp_dir_name))
    lock_file_path = lock_file.lock_file

    if force:
        logger.debug('Force mode is enabled, deleting lock file...')

        try:
            os.unlink(lock_file_path)
        except OSError:
            # Lock file doesn't exist or similar
            pass

    with lock_file:
        try:
            user_home = os.path.expanduser('~')
            abs_local_path = os.path.join(user_home, temp_dir_name)

            # 1. Clone / download the repo
            clone_repo(temp_dir=abs_local_path, repo_url=pack_url, verify_ssl=verify_ssl,
                       ref=pack_version)

            pack_ref = get_pack_ref(pack_dir=abs_local_path)
            result[1] = pack_ref

            # 2. Verify that the pack version if compatible with current StackStorm version
            if not force:
                verify_pack_version(pack_dir=abs_local_path)

            # 3. Move pack to the final location
            move_result = move_pack(abs_repo_base=abs_repo_base, pack_name=pack_ref,
                                    abs_local_path=abs_local_path,
                                    force_permissions=force_permissions,
                                    logger=logger)
            result[2] = move_result
        finally:
            cleanup_repo(abs_local_path=abs_local_path)

    return tuple(result)


def clone_repo(temp_dir, repo_url, verify_ssl=True, ref='master'):
    # Switch to non-interactive mode
    os.environ['GIT_TERMINAL_PROMPT'] = '0'
    os.environ['GIT_ASKPASS'] = '/bin/echo'

    # Disable SSL cert checking if explictly asked
    if not verify_ssl:
        os.environ['GIT_SSL_NO_VERIFY'] = 'true'

    # Clone the repo from git; we don't use shallow copying
    # because we want the user to work with the repo in the
    # future.
    repo = Repo.clone_from(repo_url, temp_dir)
    active_branch = repo.active_branch

    use_branch = False

    # Special case when a default repo branch is not "master"
    # No ref provided so we just use a default active branch
    if (not ref or ref == active_branch.name) and repo.active_branch.object == repo.head.commit:
        gitref = repo.active_branch.object
    else:
        # Try to match the reference to a branch name (i.e. "master")
        gitref = get_gitref(repo, 'origin/%s' % ref)
        if gitref:
            use_branch = True

    # Try to match the reference to a commit hash, a tag, or "master"
    if not gitref:
        gitref = get_gitref(repo, ref)

    # Try to match the reference to a "vX.Y.Z" tag
    if not gitref and re.match(PACK_VERSION_REGEX, ref):
        gitref = get_gitref(repo, 'v%s' % ref)

    # Giving up ¯\_(ツ)_/¯
    if not gitref:
        format_values = [ref, repo_url]
        msg = '"%s" is not a valid version, hash, tag or branch in %s.'

        valid_versions = get_valid_versions_for_repo(repo=repo)
        if len(valid_versions) >= 1:
            valid_versions_string = ', '.join(valid_versions)

            msg += ' Available versions are: %s.'
            format_values.append(valid_versions_string)

        raise ValueError(msg % tuple(format_values))

    # We're trying to figure out which branch the ref is actually on,
    # since there's no direct way to check for this in git-python.
    branches = repo.git.branch('-a', '--contains', gitref.hexsha)  # pylint: disable=no-member
    branches = branches.replace('*', '').split()

    if active_branch.name not in branches or use_branch:
        branch = 'origin/%s' % ref if use_branch else branches[0]
        short_branch = ref if use_branch else branches[0].split('/')[-1]
        repo.git.checkout('-b', short_branch, branch)
        branch = repo.head.reference
    else:
        branch = repo.active_branch.name

    repo.git.checkout(gitref.hexsha)  # pylint: disable=no-member
    repo.git.branch('-f', branch, gitref.hexsha)  # pylint: disable=no-member
    repo.git.checkout(branch)

    return temp_dir


def move_pack(abs_repo_base, pack_name, abs_local_path, force_permissions=True, logger=LOG):
    """
    Move pack directory into the final location.
    """
    desired, message = is_desired_pack(abs_local_path, pack_name)

    if desired:
        to = abs_repo_base
        dest_pack_path = os.path.join(abs_repo_base, pack_name)
        if os.path.exists(dest_pack_path):
            logger.debug('Removing existing pack %s in %s to replace.', pack_name,
                         dest_pack_path)

            # Ensure to preserve any existing configuration
            old_config_file = os.path.join(dest_pack_path, CONFIG_FILE)
            new_config_file = os.path.join(abs_local_path, CONFIG_FILE)

            if os.path.isfile(old_config_file):
                shutil.move(old_config_file, new_config_file)

            shutil.rmtree(dest_pack_path)

        logger.debug('Moving pack from %s to %s.', abs_local_path, to)
        shutil.move(abs_local_path, dest_pack_path)

        # post move fix all permissions
        if force_permissions:
            apply_pack_permissions(pack_path=dest_pack_path)
        message = 'Success.'
    elif message:
        message = 'Failure : %s' % message

    return (desired, message)


def apply_pack_permissions(pack_path):
    """
    Recursively apply permission 770 to pack and its contents.
    """
    # 1. switch owner group to configured group
    pack_group = utils.get_pack_group()

    if pack_group:
        shell.run_command(['sudo', 'chgrp', '-R', pack_group, pack_path])

    # 2. Setup the right permissions and group ownership
    # These mask is same as mode = 775
    mode = stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH
    os.chmod(pack_path, mode)

    # Yuck! Since os.chmod does not support chmod -R walk manually.
    for root, dirs, files in os.walk(pack_path):
        for d in dirs:
            os.chmod(os.path.join(root, d), mode)
        for f in files:
            os.chmod(os.path.join(root, f), mode)


def cleanup_repo(abs_local_path):
    # basic lock checking etc?
    if os.path.isdir(abs_local_path):
        shutil.rmtree(abs_local_path)


# Utility functions
def get_repo_url(pack, proxy_config=None):
    """
    Retrieve pack repo url.

    :rtype: ``str``

    :return: (repo_url, version)
    :rtype: tuple
    """
    pack_and_version = pack.split(PACK_VERSION_SEPARATOR)
    name_or_url = pack_and_version[0]
    version = pack_and_version[1] if len(pack_and_version) > 1 else None

    if len(name_or_url.split('/')) == 1:
        pack = get_pack_from_index(name_or_url, proxy_config=proxy_config)

        if not pack:
            raise Exception('No record of the "%s" pack in the index.' % (name_or_url))

        return (pack['repo_url'], version)
    else:
        return (eval_repo_url(name_or_url), version)


def eval_repo_url(repo_url):
    """
    Allow passing short GitHub style URLs.
    """
    if not repo_url:
        raise Exception('No valid repo_url provided or could be inferred.')

    if repo_url.startswith("file://"):
        return repo_url
    else:
        if len(repo_url.split('/')) == 2 and 'git@' not in repo_url:
            url = 'https://github.com/{}'.format(repo_url)
        else:
            url = repo_url
        return url


def is_desired_pack(abs_pack_path, pack_name):
    # path has to exist.
    if not os.path.exists(abs_pack_path):
        return (False, 'Pack "%s" not found or it\'s missing a "pack.yaml" file.' %
                (pack_name))

    # should not include reserved characters
    for character in PACK_RESERVED_CHARACTERS:
        if character in pack_name:
            return (False, 'Pack name "%s" contains reserved character "%s"' %
                    (pack_name, character))

    # must contain a manifest file. Empty file is ok for now.
    if not os.path.isfile(os.path.join(abs_pack_path, MANIFEST_FILE_NAME)):
        return (False, 'Pack is missing a manifest file (%s).' % (MANIFEST_FILE_NAME))

    return (True, '')


def verify_pack_version(pack_dir):
    """
    Verify that the pack works with the currently running StackStorm version.
    """
    pack_metadata = get_pack_metadata(pack_dir=pack_dir)
    pack_name = pack_metadata.get('name', None)
    required_stackstorm_version = pack_metadata.get('stackstorm_version', None)

    # If stackstorm_version attribute is speficied, verify that the pack works with currently
    # running version of StackStorm
    if required_stackstorm_version:
        if not complex_semver_match(CURRENT_STACKSTROM_VERSION, required_stackstorm_version):
            msg = ('Pack "%s" requires StackStorm "%s", but current version is "%s". ' %
                   (pack_name, required_stackstorm_version, CURRENT_STACKSTROM_VERSION),
                   'You can override this restriction by providing the "force" flag, but ',
                   'the pack is not guaranteed to work.')
            raise ValueError(msg)

    return True


def get_gitref(repo, ref):
    """
    Retrieve git repo reference if available.
    """
    try:
        return repo.commit(ref)
    except (BadName, BadObject):
        return False


def get_valid_versions_for_repo(repo):
    """
    Retrieve valid versions (tags) for a particular repo (pack).

    It does so by introspecting available tags.

    :rtype: ``list`` of ``str``
    """
    valid_versions = []

    for tag in repo.tags:
        if tag.name.startswith('v') and re.match(PACK_VERSION_REGEX, tag.name[1:]):
            # Note: We strip leading "v" from the version number
            valid_versions.append(tag.name[1:])

    return valid_versions


def get_pack_ref(pack_dir):
    """
    Read pack reference from the metadata file and sanitize it.
    """
    metadata = get_pack_metadata(pack_dir=pack_dir)
    pack_ref = get_pack_ref_from_metadata(metadata=metadata,
                                          pack_directory_name=None)
    return pack_ref
