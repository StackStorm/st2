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

from __future__ import absolute_import
import os
import re
import sys

from distutils.version import StrictVersion

GET_PIP = 'curl https://bootstrap.pypa.io/get-pip.py | python'

try:
    import pip
    from pip import __version__ as pip_version
except ImportError as e:
    print('Failed to import pip: %s' % (str(e)))
    print('')
    print('Download pip:\n%s' % (GET_PIP))
    sys.exit(1)

try:
    # pip < 10.0
    from pip.req import parse_requirements
except ImportError:
    # pip >= 10.0

    try:
        from pip._internal.req.req_file import parse_requirements
    except ImportError as e:
        print('Failed to import parse_requirements from pip: %s' % (str(e)))
        print('Using pip: %s' % (str(pip_version)))
        sys.exit(1)

__all__ = [
    'check_pip_version',
    'fetch_requirements',
    'apply_vagrant_workaround',
    'get_version_string',
    'parse_version_string'
]


def check_pip_version(min_version='6.0.0'):
    """
    Ensure that a minimum supported version of pip is installed.
    """
    if StrictVersion(pip.__version__) < StrictVersion(min_version):
        print("Upgrade pip, your version '{0}' "
              "is outdated. Minimum required version is '{1}':\n{2}".format(pip.__version__,
                                                                            min_version,
                                                                            GET_PIP))
        sys.exit(1)


def fetch_requirements(requirements_file_path):
    """
    Return a list of requirements and links by parsing the provided requirements file.
    """
    links = []
    reqs = []
    for req in parse_requirements(requirements_file_path, session=False):
        # Note: req.url was used before 9.0.0 and req.link is used in all the recent versions
        link = getattr(req, 'link', getattr(req, 'url', None))
        if link:
            links.append(str(link))
        reqs.append(str(req.req))
    return (reqs, links)


def apply_vagrant_workaround():
    """
    Function which detects if the script is being executed inside vagrant and if it is, it deletes
    "os.link" attribute.
    Note: Without this workaround, setup.py sdist will fail when running inside a shared directory
    (nfs / virtualbox shared folders).
    """
    if os.environ.get('USER', None) == 'vagrant':
        del os.link


def get_version_string(init_file):
    """
    Read __version__ string for an init file.
    """

    with open(init_file, 'r') as fp:
        content = fp.read()
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                                  content, re.M)
        if version_match:
            return version_match.group(1)

        raise RuntimeError('Unable to find version string in %s.' % (init_file))


# alias for get_version_string
parse_version_string = get_version_string
