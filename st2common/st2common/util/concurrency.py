# Copyright 2020-2026 The StackStorm Authors.
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
Module which acts as a compatibility later between eventlet and gevent.

It dispatches function call to the concurrency library which is configured using
"set_concurrency_library" function.
"""

try:
    import eventlet  # pylint: disable=import-error
except ImportError:
    eventlet = None

try:
    import gevent  # pylint: disable=import-error # pants: no-infer-dep
    import gevent.pool
except ImportError:
    gevent = None

CONCURRENCY_LIBRARY = "eventlet"

__all__ = [
    "set_concurrency_library",
    "get_concurrency_library",
    "get_subprocess_module",
    "subprocess_popen",
    "spawn",
    "wait",
    "cancel",
    "kill",
    "sleep",
    "get_greenlet_exit_exception_class",
    "get_green_pool_class",
    "is_green_pool_free",
    "green_pool_wait_all",
]


def set_concurrency_library(library):
    global CONCURRENCY_LIBRARY

    if library not in ["eventlet", "gevent"]:
        raise ValueError("Unsupported concurrency library: %s" % (library))

    CONCURRENCY_LIBRARY = library


def get_concurrency_library():
    global CONCURRENCY_LIBRARY
    return CONCURRENCY_LIBRARY


def get_subprocess_module():
    if CONCURRENCY_LIBRARY == "eventlet":
        from eventlet.green import subprocess  # pylint: disable=import-error

        return subprocess
    elif CONCURRENCY_LIBRARY == "gevent":
        from gevent import subprocess  # pylint: disable=import-error

        return subprocess
    else:
        raise ValueError(f"Unsupported concurrency library {CONCURRENCY_LIBRARY}")


def get_wsgi_module():
    if CONCURRENCY_LIBRARY == "eventlet":
        from eventlet import wsgi

        return wsgi
    elif CONCURRENCY_LIBRARY == "gevent":
        from gevent import pywsgi

        return pywsgi
    else:
        raise ValueError(f"Unsupported concurrency library {CONCURRENCY_LIBRARY}")


def subprocess_popen(*args, **kwargs):
    if CONCURRENCY_LIBRARY == "eventlet":
        from eventlet.green import subprocess  # pylint: disable=import-error

        return subprocess.Popen(*args, **kwargs)
    elif CONCURRENCY_LIBRARY == "gevent":
        from gevent import subprocess  # pylint: disable=import-error

        return subprocess.Popen(*args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {CONCURRENCY_LIBRARY}")


def spawn(func, *args, **kwargs):
    if CONCURRENCY_LIBRARY == "eventlet":
        return eventlet.spawn(func, *args, **kwargs)
    elif CONCURRENCY_LIBRARY == "gevent":
        return gevent.spawn(func, *args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {CONCURRENCY_LIBRARY}")


def wait(green_thread, *args, **kwargs):
    if CONCURRENCY_LIBRARY == "eventlet":
        return green_thread.wait(*args, **kwargs)
    elif CONCURRENCY_LIBRARY == "gevent":
        return green_thread.join(*args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {CONCURRENCY_LIBRARY}")


def cancel(green_thread, *args, **kwargs):
    if CONCURRENCY_LIBRARY == "eventlet":
        return green_thread.cancel(*args, **kwargs)
    elif CONCURRENCY_LIBRARY == "gevent":
        return green_thread.kill(*args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {CONCURRENCY_LIBRARY}")


def kill(green_thread, *args, **kwargs):
    if CONCURRENCY_LIBRARY == "eventlet":
        return green_thread.kill(*args, **kwargs)
    elif CONCURRENCY_LIBRARY == "gevent":
        return green_thread.kill(*args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {CONCURRENCY_LIBRARY}")


def listen(host, port):
    if CONCURRENCY_LIBRARY == "eventlet":
        return eventlet.listen((host, port))
    elif CONCURRENCY_LIBRARY == "gevent":
        raise NotImplementedError
    else:
        raise ValueError(f"Unsupported concurrency library {CONCURRENCY_LIBRARY}")


def sleep(*args, **kwargs):
    if CONCURRENCY_LIBRARY == "eventlet":
        return eventlet.sleep(*args, **kwargs)
    elif CONCURRENCY_LIBRARY == "gevent":
        return gevent.sleep(*args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {CONCURRENCY_LIBRARY}")


def get_greenlet_exit_exception_class():
    if CONCURRENCY_LIBRARY == "eventlet":
        return eventlet.support.greenlets.GreenletExit
    elif CONCURRENCY_LIBRARY == "gevent":
        return gevent.GreenletExit
    else:
        raise ValueError(f"Unsupported concurrency library {CONCURRENCY_LIBRARY}")


def get_default_green_pool_size():
    if CONCURRENCY_LIBRARY == "eventlet":
        return eventlet.wsgi.DEFAULT_MAX_SIMULTANEOUS_REQUESTS
    elif CONCURRENCY_LIBRARY == "gevent":
        # matches what DEFAULT_MAX_SIMULTANEOUS_REQUESTS is for eventlet
        return 1024
    else:
        raise ValueError("Unsupported concurrency library")


def get_green_pool_class():
    if CONCURRENCY_LIBRARY == "eventlet":
        return eventlet.GreenPool
    elif CONCURRENCY_LIBRARY == "gevent":
        return gevent.pool.Pool
    else:
        raise ValueError(f"Unsupported concurrency library {CONCURRENCY_LIBRARY}")


def is_green_pool_free(pool):
    """
    Return True if the provided green pool is free, False otherwise.
    """
    if CONCURRENCY_LIBRARY == "eventlet":
        return pool.free()
    elif CONCURRENCY_LIBRARY == "gevent":
        return not pool.full()
    else:
        raise ValueError(f"Unsupported concurrency library {CONCURRENCY_LIBRARY}")


def green_pool_wait_all(pool):
    """
    Wait for all the green threads in the pool to finish.
    """
    if CONCURRENCY_LIBRARY == "eventlet":
        return pool.waitall()
    elif CONCURRENCY_LIBRARY == "gevent":
        # NOTE: This mimicks eventlet.waitall() functionality better than
        # pool.join()
        return all(gl.ready() for gl in pool.greenlets)
    else:
        raise ValueError("Unsupported concurrency library")


def listen_server(host, port, backlog=50, **kwargs):
    """
    Start listening on the host:port.
    :backlog: the number of unaccepted connections that the system will allow before refusing new connections.
    """
    if CONCURRENCY_LIBRARY == "eventlet":
        return eventlet.listen((host, port), backlog=backlog, **kwargs)
    elif CONCURRENCY_LIBRARY == "gevent":
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, port))
        return sock.listen(backlog)
    else:
        raise ValueError("Unsupported concurrency library")


def blocking_detection(enable=False, timeout=1.0):
    if CONCURRENCY_LIBRARY == "eventlet":
        print(
            f"Eventlet long running / blocking operation detection logic enabled.  Block timeout ({timeout})."
        )
        eventlet.debug.hub_blocking_detection(enable_detection=enable, resolution=timeout)
    elif CONCURRENCY_LIBRARY == "gevent":
        print(
            f"gEvent long running / blocking operation detection logic enabled.  Block timeout ({timeout})."
        )
        gevent.config.monitor_thread = enable
        gevent.config.max_blocking_time = timeout
    else:
        raise ValueError("Unsupported concurrency library")
