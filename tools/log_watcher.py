#!/usr/bin/env python2.7
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

from __future__ import print_function
from __future__ import absolute_import
import collections
import fnmatch
import os
import re
import sys

from tabulate import tabulate
import six

LOG_ALERT_PERCENT = 5  # default.

EVILS = [
    'info',
    'debug',
    'warning',
    'exception',
    'error',
    'audit'
]

LOG_VARS = [
    'LOG',
    'Log',
    'log',
    'LOGGER',
    'Logger',
    'logger',
    'logging',
    'LOGGING'
]

FILE_LOG_COUNT = collections.defaultdict()
FILE_LINE_COUNT = collections.defaultdict()


def _parse_args(args):
    global LOG_ALERT_PERCENT
    params = {}
    if len(args) > 1:
        params['alert_percent'] = args[1]
        LOG_ALERT_PERCENT = int(args[1])
    return params


def _skip_file(filename):
    if filename.startswith('.') or filename.startswith('_'):
        return True


def _get_files(dir_path):
    if not os.path.exists(dir_path):
        print('Directory %s doesn\'t exist.' % dir_path)

    files = []
    exclude = set(['virtualenv', 'virtualenv-osx', 'build', '.tox'])
    for root, dirnames, filenames in os.walk(dir_path):
        dirnames[:] = [d for d in dirnames if d not in exclude]
        for filename in fnmatch.filter(filenames, '*.py'):
            if not _skip_file(filename):
                files.append(os.path.join(root, filename))
    return files


# TODO: Regex compiling will be faster but I cannot get it to work :(
def _build_regex():
    regex_strings = {}
    regexes = {}
    for level in EVILS:
        regex_string = '|'.join(['\.'.join([log, level]) for log in LOG_VARS])
        regex_strings[level] = regex_string
        # print('Level: %s, regex_string: %s' % (level, regex_strings[level]))
        regexes[level] = re.compile(regex_strings[level])
    return regexes


def _regex_match(line, regexes):
    pass


def _build_str_matchers():
    match_strings = {}
    for level in EVILS:
        match_strings[level] = ['.'.join([log, level]) for log in LOG_VARS]
    return match_strings


def _get_log_count_dict():
    return [(level, 0) for level in EVILS]


def _alert(fil, lines, logs, logs_level):
    print('WARNING: Too many logs!!!: File: %s, total lines: %d, log lines: %d, percent: %f, '
          'logs: %s' % (fil, lines, logs, float(logs) / lines * 100, logs_level))


def _match(line, match_strings):
    for level, match_strings in six.iteritems(match_strings):
        for match_string in match_strings:
            if line.startswith(match_string):
                # print('Line: %s, match: %s' % (line, match_string))
                return True, level, line
    return False, 'UNKNOWN', line


def _detect_log_lines(fil, matchers):
    global FILE_LOG_COUNT
    FILE_LOG_COUNT[fil] = dict(_get_log_count_dict())
    # print('Working on file: %s' % fil)
    with open(fil) as f:
        lines = f.readlines()
        FILE_LINE_COUNT[fil] = len(lines)

        ln = 0
        for line in lines:
            line = line.strip()
            ln += 1
            matched, level, line = _match(line, matchers)
            if matched:
                # print('File: %s, Level: %s, Line: %d:%s' % (fil, level, ln, line.strip()))
                FILE_LOG_COUNT[fil][level] += 1


def _post_process(file_dir):
    alerts = []
    for fil, lines in six.iteritems(FILE_LINE_COUNT):
        log_lines_count_level = FILE_LOG_COUNT[fil]
        total_log_count = 0
        for level, count in six.iteritems(log_lines_count_level):
            total_log_count += count
        if total_log_count > 0:
            if float(total_log_count) / lines * 100 > LOG_ALERT_PERCENT:
                if file_dir in fil:
                    fil = fil[len(file_dir) + 1:]
                alerts.append([fil, lines, total_log_count, float(total_log_count) / lines * 100,
                               log_lines_count_level['audit'],
                               log_lines_count_level['exception'],
                               log_lines_count_level['error'],
                               log_lines_count_level['warning'],
                               log_lines_count_level['info'],
                               log_lines_count_level['debug']])
    # sort by percent
    alerts.sort(key=lambda alert: alert[3], reverse=True)
    print(tabulate(alerts, headers=['File', 'Lines', 'Logs', 'Percent', 'adt', 'exc', 'err', 'wrn',
                                    'inf', 'dbg']))


def main(args):
    params = _parse_args(args)
    file_dir = params.get('dir', os.getcwd())
    files = _get_files(file_dir)
    matchers = _build_str_matchers()
    for f in files:
        _detect_log_lines(f, matchers)
    _post_process(file_dir)


if __name__ == '__main__':
    main(sys.argv)
