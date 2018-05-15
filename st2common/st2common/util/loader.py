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

import imp
import inspect
import json
import os
import sys
from collections import defaultdict

import six
import yaml
from oslo_config import cfg

from st2common.exceptions.plugins import IncompatiblePluginException
from st2common import log as logging

__all__ = [
    'register_plugin',
    'register_plugin_class',

    'register_runner',
    'register_query_module',
    'register_callback_module',

    'load_meta_file'
]


LOG = logging.getLogger(__name__)

PYTHON_EXTENSION = '.py'
ALLOWED_EXTS = ['.json', '.yaml', '.yml']
PARSER_FUNCS = {'.json': json.load, '.yml': yaml.safe_load, '.yaml': yaml.safe_load}

# Cache for dynamically loaded runner modules
RUNNER_MODULES_CACHE = defaultdict(dict)
QUERIER_MODULES_CACHE = {}
CALLBACK_MODULES_CACHE = {}


def _register_plugin_path(plugin_dir_abs_path):
    if not os.path.isdir(plugin_dir_abs_path):
        raise Exception('Directory "%s" with plugins doesn\'t exist' % (plugin_dir_abs_path))

    for x in sys.path:
        if plugin_dir_abs_path in (x, x + os.sep):
            return
    sys.path.append(plugin_dir_abs_path)


def _get_plugin_module(plugin_file_path):
    plugin_module = os.path.basename(plugin_file_path)
    if plugin_module.endswith(PYTHON_EXTENSION):
        plugin_module = plugin_module[:plugin_module.rfind('.py')]
    else:
        plugin_module = None
    return plugin_module


def _get_classes_in_module(module):
    return [kls for name, kls in inspect.getmembers(module,
            lambda member: inspect.isclass(member) and member.__module__ == module.__name__)]


def _get_plugin_classes(module_name):
    return _get_classes_in_module(module_name)


def _get_plugin_methods(plugin_klass):
    """
    Return a list of names of all the methods in the provided class.

    Note: Abstract methods which are not implemented are excluded from the
    list.

    :rtype: ``list`` of ``str``
    """
    if six.PY3:
        methods = inspect.getmembers(plugin_klass, inspect.isfunction)
    else:
        methods = inspect.getmembers(plugin_klass, inspect.ismethod)

    # Exclude inherited abstract methods from the parent class
    method_names = []
    for name, method in methods:
        method_properties = method.__dict__
        is_abstract = method_properties.get('__isabstractmethod__', False)

        if is_abstract:
            continue

        method_names.append(name)
    return method_names


def _validate_methods(plugin_base_class, plugin_klass):
    '''
    XXX: This is hacky but we'd like to validate the methods
    in plugin_impl at least has all the *abstract* methods in
    plugin_base_class.
    '''
    expected_methods = plugin_base_class.__abstractmethods__
    plugin_methods = _get_plugin_methods(plugin_klass)
    for method in expected_methods:
        if method not in plugin_methods:
            message = 'Class "%s" doesn\'t implement required "%s" method from the base class'
            raise IncompatiblePluginException(message % (plugin_klass.__name__, method))


def _register_plugin(plugin_base_class, plugin_impl):
    _validate_methods(plugin_base_class, plugin_impl)
    plugin_base_class.register(plugin_impl)


def register_plugin_class(base_class, file_path, class_name):
    """
    Retrieve a register plugin class from the provided file.

    This method also validate that the class implements all the abstract methods
    from the base plugin class.

    :param base_class: Base plugin class.
    :param base_class: ``class``

    :param file_path: File absolute path to the plugin module file.
    :type file_path: ``str``

    :param class_name: Class name of a plugin.
    :type class_name: ``str``
    """
    plugin_dir = os.path.dirname(os.path.realpath(file_path))
    _register_plugin_path(plugin_dir)
    module_name = _get_plugin_module(file_path)

    if module_name is None:
        return None

    module = imp.load_source(module_name, file_path)
    klass = getattr(module, class_name, None)

    if not klass:
        raise Exception('Plugin file "%s" doesn\'t expose class named "%s"' %
                        (file_path, class_name))

    _register_plugin(base_class, klass)
    return klass


def register_plugin(plugin_base_class, plugin_abs_file_path):
    registered_plugins = []
    plugin_dir = os.path.dirname(os.path.realpath(plugin_abs_file_path))
    _register_plugin_path(plugin_dir)

    module_name = _get_plugin_module(plugin_abs_file_path)
    if module_name is None:
        return None

    module = imp.load_source(module_name, plugin_abs_file_path)
    klasses = _get_plugin_classes(module)

    # Try registering classes in plugin file. Some may fail.
    for klass in klasses:
        try:
            _register_plugin(plugin_base_class, klass)
            registered_plugins.append(klass)
        except Exception as e:
            LOG.exception(e)
            LOG.debug('Skipping class %s as it doesn\'t match specs.', klass)
            continue

    if len(registered_plugins) == 0:
        raise Exception('Found no classes in plugin file "%s" matching requirements.' %
                        (plugin_abs_file_path))

    return registered_plugins


def register_runner(package_name, module_name):
    # TODO: Switch to stevedore enumeration and loading
    base_path = cfg.CONF.system.base_path

    # 1. First try post StackStorm v2.6.0 path (runners are Python packages)
    module_path = os.path.join(base_path, 'runners', package_name, package_name,
                               module_name + '.py')

    # 2. Second try pre StackStorm v2.6.0 path (runners are not Python packages)
    if not os.path.isfile(module_path):
        module_path = os.path.join(base_path, 'runners', module_name, module_name + '.py')

    if not RUNNER_MODULES_CACHE.get(package_name, {}).get(module_name, None):
        LOG.info('Loading runner module from "%s".', module_path)

        # Make sure all the runner packages are in PYTHONPATH
        # Note: This won't be needed anymore when we modify this code so it also works under
        # Python 3 and move away from imp.load_source
        package_directory = os.path.abspath(os.path.join(os.path.dirname(module_path), '../'))

        if os.path.isdir(package_directory) and package_directory not in sys.path:
            LOG.debug('Adding runner package directory "%s" to PYTHONPATH' % (package_directory))
            sys.path.append(package_directory)

        load_name = '%s.%s' % (package_name, module_name)
        RUNNER_MODULES_CACHE[package_name][module_name] = imp.load_source(load_name, module_path)
    else:
        LOG.info('Reusing runner module "%s" from cache.', module_path)

    return RUNNER_MODULES_CACHE[package_name][module_name]


def register_query_module(module_name):
    base_path = cfg.CONF.system.base_path
    module_path = os.path.join(base_path, 'runners', module_name, 'query', module_name + '.py')

    if module_name not in QUERIER_MODULES_CACHE:
        LOG.info('Loading query module from "%s".', module_path)
        QUERIER_MODULES_CACHE[module_name] = imp.load_source(module_name, module_path)
    else:
        LOG.info('Reusing query module "%s" from cache.', module_path)

    return QUERIER_MODULES_CACHE[module_name]


def register_callback_module(module_name):
    base_path = cfg.CONF.system.base_path
    module_path = os.path.join(base_path, 'runners', module_name, 'callback', module_name + '.py')

    if module_name not in CALLBACK_MODULES_CACHE:
        LOG.info('Loading callback module from "%s".', module_path)
        CALLBACK_MODULES_CACHE[module_name] = imp.load_source(module_name, module_path)
    else:
        LOG.info('Reusing callback module "%s" from cache.', module_path)

    return CALLBACK_MODULES_CACHE[module_name]


def load_meta_file(file_path):
    if not os.path.isfile(file_path):
        raise Exception('File "%s" does not exist.' % file_path)

    file_name, file_ext = os.path.splitext(file_path)
    if file_ext not in ALLOWED_EXTS:
        raise Exception('Unsupported meta type %s, file %s. Allowed: %s' %
                        (file_ext, file_path, ALLOWED_EXTS))

    with open(file_path, 'r') as f:
        return PARSER_FUNCS[file_ext](f)


def get_available_plugins(namespace):
    """Return names of the available / installed plugins for a given namespace.
    """
    from stevedore.extension import ExtensionManager

    manager = ExtensionManager(namespace=namespace, invoke_on_load=False)
    return manager.names()


def get_plugin_instance(namespace, name):
    """Return class instance for the provided plugin name and namespace.
    """
    from stevedore.driver import DriverManager

    manager = DriverManager(namespace=namespace, name=name, invoke_on_load=True)
    return manager.driver
