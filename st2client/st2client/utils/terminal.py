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
import struct
import subprocess
import sys

from st2client.utils.color import format_status

__all__ = [
    'get_terminal_size'
]


def get_terminal_size(default=(80, 20)):
    """
    :return: (lines, cols)
    """
    def ioctl_GWINSZ(fd):
        import fcntl
        import termios
        return struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
    # try stdin, stdout, stderr
    for fd in (0, 1, 2):
        try:
            return ioctl_GWINSZ(fd)
        except:
            pass
    # try os.ctermid()
    try:
        fd = os.open(os.ctermid(), os.O_RDONLY)
        try:
            return ioctl_GWINSZ(fd)
        finally:
            os.close(fd)
    except:
        pass
    # try `stty size`
    try:
        process = subprocess.Popen(['stty', 'size'],
                                   shell=False,
                                   stdout=subprocess.PIPE,
                                   stderr=open(os.devnull, 'w'))
        result = process.communicate()
        if process.returncode == 0:
            return tuple(int(x) for x in result[0].split())
    except:
        pass
    # try environment variables
    try:
        return tuple(int(os.getenv(var)) for var in ('LINES', 'COLUMNS'))
    except:
        pass
    #  return default.
    return default


class TaskIndicator(object):
    def __enter__(self):
        self.dirty = False
        return self

    def __exit__(self, type, value, traceback):
        return self.close()

    def add_stage(self, status, name):
        self._write('\t[{:^20}] {}'.format(format_status(status), name))

    def update_stage(self, status, name):
        self._write('\t[{:^20}] {}'.format(format_status(status), name), override=True)

    def finish_stage(self, status, name):
        self._write('\t[{:^20}] {}'.format(format_status(status), name), override=True)

    def close(self):
        if self.dirty:
            self._write('\n')

    def _write(self, string, override=False):
        if override:
            sys.stdout.write('\r')
        else:
            sys.stdout.write('\n')

        sys.stdout.write(string)
        sys.stdout.flush()

        self.dirty = True
