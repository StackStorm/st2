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
import socket

import psutil

__all__ = [
    'get_host_info',
    'get_process_info'
]


def get_host_info():
    host_info = {
        'hostname': socket.gethostname()
    }
    return host_info


def get_process_info():
    try:
        p = psutil.Process(os.getpid())
        name = p.name()
    except Exception:
        name = 'unknown'

    process_info = {
        'hostname': socket.gethostname(),
        'pid': os.getpid()
    }

    try:
        p = psutil.Process(os.getpid())
        name = p.name()
    except Exception:
        pass
    else:
        process_info['name'] = name

    return process_info
