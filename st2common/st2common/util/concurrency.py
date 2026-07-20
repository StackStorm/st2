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

import os

try:
    import eventlet  # pylint: disable=import-error
except ImportError:
    eventlet = None

try:
    import gevent  # pylint: disable=import-error # pants: no-infer-dep
    import gevent.lock
    import gevent.pool
    import gevent.queue
except ImportError:
    gevent = None

CONCURRENCY_LIBRARY = os.environ.get("ST2_CONCURRENCY_LIBRARY", "eventlet")

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


def wsgi_server(
    socket, app, custom_pool=None, log=None, log_output=True, *args, **kwargs
):
    if CONCURRENCY_LIBRARY == "eventlet":
        from eventlet import wsgi

        wsgi.server(
            socket,
            app,
            custom_pool=custom_pool,
            log=log,
            log_output=log_output,
            *args,
            **kwargs,
        )
    elif CONCURRENCY_LIBRARY == "gevent":
        from gevent import pywsgi

        server = pywsgi.WSGIServer(socket, app, spawn=custom_pool, log=log)
        server.serve_forever()
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


def spawn_after(seconds, func, *args, **kwargs):
    if CONCURRENCY_LIBRARY == "eventlet":
        return eventlet.spawn_after(seconds, func, *args, **kwargs)
    elif CONCURRENCY_LIBRARY == "gevent":
        return gevent.spawn_later(seconds, func, *args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {CONCURRENCY_LIBRARY}")


def Semaphore(*args, **kwargs):
    if CONCURRENCY_LIBRARY == "eventlet":
        return eventlet.Semaphore(*args, **kwargs)
    elif CONCURRENCY_LIBRARY == "gevent":
        return gevent.lock.Semaphore(*args, **kwargs)
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
    return listen_server(host, port)


def Queue(*args, **kwargs):
    if CONCURRENCY_LIBRARY == "eventlet":
        return eventlet.Queue(*args, **kwargs)
    elif CONCURRENCY_LIBRARY == "gevent":
        return gevent.queue.Queue(*args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {CONCURRENCY_LIBRARY}")


def get_queue_empty_exception():
    if CONCURRENCY_LIBRARY == "eventlet":
        return eventlet.queue.Empty
    elif CONCURRENCY_LIBRARY == "gevent":
        return gevent.queue.Empty
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


def green_pool_free_count(pool):
    """
    Return the number of free slots in the pool.
    """
    if CONCURRENCY_LIBRARY == "eventlet":
        return pool.free()
    elif CONCURRENCY_LIBRARY == "gevent":
        return pool.free_count()
    else:
        raise ValueError(f"Unsupported concurrency library {CONCURRENCY_LIBRARY}")


def is_green_pool_free(pool):
    """
    Return True if the provided green pool has at least one free slot, False otherwise.
    """
    return green_pool_free_count(pool) > 0


def green_pool_running_count(pool):
    """
    Return the number of greenlets currently running in the pool.
    """
    if CONCURRENCY_LIBRARY == "eventlet":
        return pool.running()
    elif CONCURRENCY_LIBRARY == "gevent":
        return len(pool.greenlets)
    else:
        raise ValueError("Unsupported concurrency library")


def get_pool_greenlets(pool):
    """
    Return the set of currently running greenlets in the pool.
    """
    if CONCURRENCY_LIBRARY == "eventlet":
        return pool.coroutines_running
    elif CONCURRENCY_LIBRARY == "gevent":
        return pool.greenlets
    else:
        raise ValueError("Unsupported concurrency library")


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
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(backlog)
        return sock
    else:
        raise ValueError("Unsupported concurrency library")


def wrap_ssl(socket, *args, **kwargs):
    if CONCURRENCY_LIBRARY == "eventlet":
        return eventlet.wrap_ssl(socket, *args, **kwargs)
    elif CONCURRENCY_LIBRARY == "gevent":
        # Monkey patching in the caller module is required prior to
        # calling wrap_ssl() or this may block.
        import ssl

        return ssl.wrap_socket(socket, *args, **kwargs)
    else:
        raise ValueError("Unsupported concurrency library")


def blocking_detection(enable=False, timeout=1.0):
    if CONCURRENCY_LIBRARY == "eventlet":
        print(
            f"Eventlet long running / blocking operation detection logic enabled.  Block timeout ({timeout})."
        )
        eventlet.debug.hub_blocking_detection(state=enable, resolution=timeout)
    elif CONCURRENCY_LIBRARY == "gevent":
        print(
            f"gEvent long running / blocking operation detection logic enabled.  Block timeout ({timeout})."
        )
        gevent.config.monitor_thread = enable
        gevent.config.max_blocking_time = timeout
    else:
        raise ValueError("Unsupported concurrency library")
