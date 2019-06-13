# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Compatibility layer which supports two sets of concurrency libraries - eventlet and gevent.
"""

try:
    import eventlet
except ImportError:
    eventlet = None

try:
    import gevent
except ImportError:
    gevent = None

CONCURRENCY_LIBRARY = 'eventlet'

__all__ = [
    'set_concurrency_library',

    'get_subprocess_module',

    'spawn',
    'wait',
    'cancel',
    'kill'
]


def set_concurrency_library(library):
    global CONCURRENCY_LIBRARY

    if library not in ['eventlet', 'gevent']:
        raise ValueError('Unsupported concurrency library: %s' % (library))

    CONCURRENCY_LIBRARY = library


def get_subprocess_module():
    if CONCURRENCY_LIBRARY == 'eventlet':
        from eventlet.green import subprocess
        return subprocess
    elif CONCURRENCY_LIBRARY == 'gevent':
        from gevent import subprocess
        return subprocess
    else:
        raise ValueError('Unsupported concurrency library')


def spawn(func, *args, **kwargs):
    if CONCURRENCY_LIBRARY == 'eventlet':
        return eventlet.spawn(func, *args, **kwargs)
    elif CONCURRENCY_LIBRARY == 'gevent':
        return gevent.spawn(func, *args, **kwargs)
    else:
        raise ValueError('Unsupported concurrency library')


def wait(green_thread, *args, **kwargs):
    if CONCURRENCY_LIBRARY == 'eventlet':
        return green_thread.wait(*args, **kwargs)
    elif CONCURRENCY_LIBRARY == 'gevent':
        return green_thread.join(*args, **kwargs)
    else:
        raise ValueError('Unsupported concurrency library')


def cancel(green_thread, *args, **kwargs):
    if CONCURRENCY_LIBRARY == 'eventlet':
        return green_thread.cancel(*args, **kwargs)
    elif CONCURRENCY_LIBRARY == 'gevent':
        return green_thread.kill(*args, **kwargs)
    else:
        raise ValueError('Unsupported concurrency library')


def kill(green_thread, *args, **kwargs):
    if CONCURRENCY_LIBRARY == 'eventlet':
        return green_thread.kill(*args, **kwargs)
    elif CONCURRENCY_LIBRARY == 'gevent':
        return green_thread.kill(*args, **kwargs)
    else:
        raise ValueError('Unsupported concurrency library')
