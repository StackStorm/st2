#!/usr/bin/env python
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
A utility script which sends test messages to a queue.
"""

import argparse
import fnmatch
try:
    import simplejson as json
except ImportError:
    import json
import os
import pprint
import subprocess
import traceback
import yaml


PRINT = pprint.pprint
YAML_HEADER = '---'


def get_files_matching_pattern(dir_, pattern):
    files = []
    for root, _, filenames in os.walk(dir_):
        for filename in fnmatch.filter(filenames, pattern):
            files.append(os.path.join(root, filename))
    return files


def json_2_yaml_convert(filename):
    data = None
    try:
        with open(filename, 'r') as json_file:
            data = json.load(json_file)
    except:
        PRINT('Failed on {}'.format(filename))
        traceback.print_exc()
        return (filename, '')
    new_filename = os.path.splitext(filename)[0] + '.yaml'
    with open(new_filename, 'w') as yaml_file:
        yaml_file.write(YAML_HEADER + '\n')
        yaml_file.write(yaml.safe_dump(data, default_flow_style=False))
    return (filename, new_filename)


def git_rm(filename):
    try:
        subprocess.check_call(['git', 'rm', filename])
    except subprocess.CalledProcessError:
        PRINT('Failed to git rm {}'.format(filename))
        traceback.print_exc()
        return (False, filename)
    return (True, filename)


def main(dir_, skip_convert):
    files = get_files_matching_pattern(dir_, '*.json')
    if skip_convert:
        PRINT(files)
        return
    results = [json_2_yaml_convert(filename) for filename in files]
    PRINT('*** conversion done ***')
    PRINT(['converted {} to {}'.format(result[0], result[1]) for result in results])
    results = [git_rm(filename) for filename, new_filename in results if new_filename]
    PRINT('*** git rm done ***')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='json2yaml converter.')
    parser.add_argument('--dir', '-d', required=True,
                        help='The dir to look for json.')
    parser.add_argument('--skipconvert', '-s', action='store_true',
                        help='Skip conversion')
    args = parser.parse_args()

    main(dir_=args.dir, skip_convert=args.skipconvert)
