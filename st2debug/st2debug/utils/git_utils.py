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

from st2common.util.shell import run_command

__all__ = [
    'get_repo_latest_revision_hash'
]


def get_repo_latest_revision_hash(repo_path):
    """
    Return a hash to the latest revision in the provided repo.

    :param repo_path: Path to the git repository.
    :type repo_path: ``str``

    :rtype: ``str``
    """
    try:
        exit_code, stdout, _ = run_command(cmd=['git', 'rev-parse', 'HEAD'],
                                           cwd=repo_path)
    except Exception:
        revision_hash = 'unknown'
    else:
        if exit_code == 0:
            revision_hash = stdout.strip()
        else:
            revision_hash = 'unknown'

    return revision_hash
