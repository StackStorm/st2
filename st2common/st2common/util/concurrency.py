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

import configparser
import cProfile
import types

from st2common.constants.system import DEFAULT_CONFIG_FILE_PATH

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
    "get_green_profiler",
]

_state = types.SimpleNamespace(library=None, eventlet=None, gevent=None)


def _get_concurrency_library_from_conf(config_path=DEFAULT_CONFIG_FILE_PATH):
    # NOTE: We can't use st2common.config/oslo_config here because eventlet/gevent
    # monkey patching (see st2common.util.monkey_patch) must happen before almost
    # anything else is imported, which is earlier than oslo_config can be parsed.
    # This minimal read only depends on the stdlib.
    parser = configparser.ConfigParser()
    parser.read(config_path)  # no-op if the file doesn't exist
    try:
        return parser.get("system", "concurrency_library")
    except (configparser.NoSectionError, configparser.NoOptionError):
        return "gevent"


def _import_eventlet():
    try:
        import eventlet  # pylint: disable=import-error
        import eventlet.debug
        import eventlet.green.profile
        import eventlet.green.subprocess
        import eventlet.wsgi

        return eventlet
    except ImportError:
        return None


def _import_gevent():
    try:
        import gevent  # pylint: disable=import-error # pants: no-infer-dep
        import gevent.lock
        import gevent.monkey
        import gevent.pool
        import gevent.pywsgi
        import gevent.queue
        import gevent.subprocess

        return gevent
    except ImportError:
        return None


def set_concurrency_library(library):
    if library not in ("eventlet", "gevent"):
        raise ValueError("Unsupported concurrency library: %s" % (library))

    # Only import the library that's actually active. Importing eventlet unconditionally
    # eagerly loads eventlet.green.ssl, subclassing ssl.SSLContext before
    # gevent.monkey.patch_all() runs, which triggers a spurious MonkeyPatchWarning.
    if library == "eventlet" and _state.eventlet is None:
        _state.eventlet = _import_eventlet()
    elif library == "gevent" and _state.gevent is None:
        _state.gevent = _import_gevent()

    _state.library = library


def get_concurrency_library():
    return _state.library


set_concurrency_library(_get_concurrency_library_from_conf())


def get_subprocess_module():
    if _state.library == "eventlet":
        return _state.eventlet.green.subprocess
    elif _state.library == "gevent":
        return _state.gevent.subprocess
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def wsgi_server(
    socket, app, custom_pool=None, log=None, log_output=True, *args, **kwargs
):
    if _state.library == "eventlet":
        _state.eventlet.wsgi.server(
            socket,
            app,
            custom_pool=custom_pool,
            log=log,
            log_output=log_output,
            *args,
            **kwargs,
        )
    elif _state.library == "gevent":
        server = _state.gevent.pywsgi.WSGIServer(
            socket, app, spawn=custom_pool, log=log
        )
        server.serve_forever()
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def subprocess_popen(*args, **kwargs):
    if _state.library == "eventlet":
        return _state.eventlet.green.subprocess.Popen(*args, **kwargs)
    elif _state.library == "gevent":
        return _state.gevent.subprocess.Popen(*args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def spawn_after(seconds, func, *args, **kwargs):
    if _state.library == "eventlet":
        return _state.eventlet.spawn_after(seconds, func, *args, **kwargs)
    elif _state.library == "gevent":
        return _state.gevent.spawn_later(seconds, func, *args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def Semaphore(*args, **kwargs):
    if _state.library == "eventlet":
        return _state.eventlet.Semaphore(*args, **kwargs)
    elif _state.library == "gevent":
        return _state.gevent.lock.Semaphore(*args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def spawn(func, *args, **kwargs):
    if _state.library == "eventlet":
        return _state.eventlet.spawn(func, *args, **kwargs)
    elif _state.library == "gevent":
        return _state.gevent.spawn(func, *args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def wait(green_thread, *args, **kwargs):
    if _state.library == "eventlet":
        return green_thread.wait(*args, **kwargs)
    elif _state.library == "gevent":
        # NOTE: Greenlet.join() blocks but always returns None; .get() blocks
        # and returns the greenlet's result (or re-raises its exception),
        # matching eventlet's GreenThread.wait() semantics.
        return green_thread.get(*args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def cancel(green_thread, *args, **kwargs):
    if _state.library == "eventlet":
        return green_thread.cancel(*args, **kwargs)
    elif _state.library == "gevent":
        return green_thread.kill(*args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def kill(green_thread, *args, **kwargs):
    if _state.library == "eventlet":
        return green_thread.kill(*args, **kwargs)
    elif _state.library == "gevent":
        return green_thread.kill(*args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def listen(host, port):
    return listen_server(host, port)


def Queue(*args, **kwargs):
    if _state.library == "eventlet":
        return _state.eventlet.Queue(*args, **kwargs)
    elif _state.library == "gevent":
        return _state.gevent.queue.Queue(*args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def get_queue_empty_exception():
    if _state.library == "eventlet":
        return _state.eventlet.queue.Empty
    elif _state.library == "gevent":
        return _state.gevent.queue.Empty
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def sleep(*args, **kwargs):
    if _state.library == "eventlet":
        return _state.eventlet.sleep(*args, **kwargs)
    elif _state.library == "gevent":
        return _state.gevent.sleep(*args, **kwargs)
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def get_greenlet_exit_exception_class():
    if _state.library == "eventlet":
        return _state.eventlet.support.greenlets.GreenletExit
    elif _state.library == "gevent":
        return _state.gevent.GreenletExit
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def get_default_green_pool_size():
    if _state.library == "eventlet":
        return _state.eventlet.wsgi.DEFAULT_MAX_SIMULTANEOUS_REQUESTS
    elif _state.library == "gevent":
        # matches what DEFAULT_MAX_SIMULTANEOUS_REQUESTS is for eventlet
        return 1024
    else:
        raise ValueError("Unsupported concurrency library")


def get_green_pool_class():
    if _state.library == "eventlet":
        return _state.eventlet.GreenPool
    elif _state.library == "gevent":
        return _state.gevent.pool.Pool
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def green_pool_free_count(pool):
    """
    Return the number of free slots in the pool.
    """
    if _state.library == "eventlet":
        return pool.free()
    elif _state.library == "gevent":
        return pool.free_count()
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def is_green_pool_free(pool):
    """
    Return True if the provided green pool has at least one free slot, False otherwise.
    """
    return green_pool_free_count(pool) > 0


def green_pool_running_count(pool):
    """
    Return the number of greenlets currently running in the pool.
    """
    if _state.library == "eventlet":
        return pool.running()
    elif _state.library == "gevent":
        return len(pool.greenlets)
    else:
        raise ValueError("Unsupported concurrency library")


def get_pool_greenlets(pool):
    """
    Return the set of currently running greenlets in the pool.
    """
    if _state.library == "eventlet":
        return pool.coroutines_running
    elif _state.library == "gevent":
        return pool.greenlets
    else:
        raise ValueError("Unsupported concurrency library")


def green_pool_wait_all(pool):
    """
    Wait for all the green threads in the pool to finish.
    """
    if _state.library == "eventlet":
        return pool.waitall()
    elif _state.library == "gevent":
        return pool.join()
    else:
        raise ValueError("Unsupported concurrency library")


def listen_server(host, port, backlog=50, **kwargs):
    """
    Start listening on the host:port.
    :backlog: the number of unaccepted connections that the system will allow before refusing new connections.
    """
    if _state.library == "eventlet":
        return _state.eventlet.listen((host, port), backlog=backlog, **kwargs)
    elif _state.library == "gevent":
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(backlog)
        return sock
    else:
        raise ValueError("Unsupported concurrency library")


def wrap_ssl(socket, *args, **kwargs):
    if _state.library == "eventlet":
        return _state.eventlet.wrap_ssl(socket, *args, **kwargs)
    elif _state.library == "gevent":
        # Monkey patching in the caller module is required prior to
        # calling wrap_ssl() or this may block.
        import ssl

        server_side = kwargs.pop("server_side", False)
        certfile = kwargs.pop("certfile", None)
        keyfile = kwargs.pop("keyfile", None)

        protocol = ssl.PROTOCOL_TLS_SERVER if server_side else ssl.PROTOCOL_TLS_CLIENT
        context = ssl.SSLContext(protocol)
        if certfile:
            context.load_cert_chain(certfile, keyfile)

        return context.wrap_socket(socket, *args, server_side=server_side, **kwargs)
    else:
        raise ValueError("Unsupported concurrency library")


def get_green_profiler():
    """
    Return a (profiler, start, stop) tuple for a green-thread-aware profiler.

    Only to be used with eventlet/gevent code (aka a StackStorm service minus the CLI).
    """
    if _state.library == "eventlet":
        if not _state.eventlet.patcher.is_monkey_patched("os"):
            raise ValueError(
                "No eventlet monkey patching detected. Code may not be using eventlet"
            )

        profiler = _state.eventlet.green.profile.Profile()
        return profiler, profiler.start, profiler.stop
    elif _state.library == "gevent":
        if not _state.gevent.monkey.is_module_patched("os"):
            raise ValueError(
                "No gevent monkey patching detected. Code may not be using gevent"
            )

        # gevent doesn't ship a greenlet-aware profile module; regular cProfile works fine
        # since gevent greenlets are cooperative and run on a single OS thread.
        profiler = cProfile.Profile()
        return profiler, profiler.enable, profiler.disable
    else:
        raise ValueError(f"Unsupported concurrency library {_state.library}")


def blocking_detection(enable=False, timeout=1.0):
    if _state.library == "eventlet":
        print(
            f"Eventlet long running / blocking operation detection logic enabled.  Block timeout ({timeout})."
        )
        _state.eventlet.debug.hub_blocking_detection(state=enable, resolution=timeout)
    elif _state.library == "gevent":
        print(
            f"gEvent long running / blocking operation detection logic enabled.  Block timeout ({timeout})."
        )
        _state.gevent.config.monitor_thread = enable
        _state.gevent.config.max_blocking_time = timeout
    else:
        raise ValueError("Unsupported concurrency library")
