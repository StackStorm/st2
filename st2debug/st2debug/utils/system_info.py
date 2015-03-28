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

import re

from st2common.util.shell import run_command
from st2common.util.shell import quote_unix

__all__ = [
    'get_cpu_info',
    'get_memory_info',
    'get_package_list',
    'get_deb_package_list',
    'get_rpm_package_list'
]

CPU_INFO_PATH = '/proc/cpuinfo'
MEMORY_INFO_PATH = '/proc/meminfo'


def get_cpu_info():
    """
    Retrieve CPU information.

    :return: List which contain dictionary with information for each core / CPU.
    :rtype: ``list`` of ``dict``
    """
    try:
        with open(CPU_INFO_PATH) as fp:
            content = fp.read()
    except IOError:
        return {}

    lines = content.split('\n')

    result = []
    item = None
    lines_count = len(lines)
    for index, line in enumerate(lines):
        line = line.strip()

        if not line:
            if item and index != lines_count:
                result.append(item)
            continue

        split = line.split(':')

        if len(split) != 2:
            continue

        name = split[0].replace('\t', '').strip().replace(' ', '_')
        value = split[1].replace('\t', '').strip()

        if name == 'processor':
            # Info about new core / CPU
            item = {}

        item[name] = value

    return result


def get_memory_info():
    """
    Retrieve memory information.

    :rtype: ``dict``
    """
    try:
        with open(MEMORY_INFO_PATH) as fp:
            content = fp.read()
    except IOError:
        return {}

    lines = content.split('\n')

    result = {}
    for line in lines:
        line = line.strip()

        if not line:
            continue

        split = line.split(':')
        name = split[0].strip()
        value = split[1].replace('kB', '').strip()

        try:
            value = int(value)
        except Exception:
            continue

        result[name] = value

    return result


def get_package_list(name_startswith):
    """
    Retrieve system packages which name matches the provided startswith filter.

    Note: This function only supports Debian and RedHat based systems.

    :param name_startswith: Package name startswith filter string.
    :type name_startswith: ``str``

    :rtype: ``list`` of ``dict``
    """
    dpkg_exit_code, _, _ = run_command(cmd='dpkg', shell=True)
    rpm_exit_code, _, _ = run_command(cmd='rpm', shell=True)

    if dpkg_exit_code != 127:
        result = get_deb_package_list(name_startswith=name_startswith)
    elif rpm_exit_code != 127:
        result = get_rpm_package_list(name_startswith=name_startswith)
    else:
        raise Exception('Unsupported platform (dpkg or rpm binary not available)')

    return result


def get_deb_package_list(name_startswith):
    cmd = 'dpkg -l | grep %s' % (quote_unix(name_startswith))
    exit_code, stdout, _ = run_command(cmd=cmd, shell=True)

    lines = stdout.split('\n')

    packages = []
    for line in lines:
        line = line.strip()

        if not line:
            continue

        split = re.split('\s+', line)
        name = split[1]
        version = split[2]

        if not name.startswith(name_startswith):
            continue

        item = {
            'name': name,
            'version': version
        }
        packages.append(item)

    return packages


def get_rpm_package_list(name_startswith):
    cmd = 'rpm -qa | grep %s' % (quote_unix(name_startswith))
    exit_code, stdout, _ = run_command(cmd=cmd, shell=True)

    lines = stdout.split('\n')

    packages = []
    for line in lines:
        line = line.strip()

        if not line:
            continue

        split = line.rsplit('.', 1)
        split = split[0].split('-', 1)
        name = split[0]
        version = split[1]

        if not name.startswith(name_startswith):
            continue

        item = {
            'name': name,
            'version': version
        }
        packages.append(item)

    return packages
