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

import importlib
import inspect
import os
import sys

from st2common.exceptions.plugins import IncompatiblePluginException
from st2common import log as logging


LOG = logging.getLogger(__name__)
PYTHON_EXTENSIONS = ('.py')


def _register_plugin_path(plugin_dir_abs_path):
    if not os.path.isdir(plugin_dir_abs_path):
        raise Exception('Directory containing plugins must be provided.')
    for x in sys.path:
        if plugin_dir_abs_path in (x, x + os.sep):
            return
    sys.path.append(plugin_dir_abs_path)


def _get_plugin_module(plugin_file_path):
    plugin_module = os.path.basename(plugin_file_path)
    if plugin_module.endswith(PYTHON_EXTENSIONS):
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
            raise IncompatiblePluginException('Class %s does not implement method %s in base class.'
                            % (plugin_klass, method))


def _register_plugin(plugin_base_class, plugin_impl):
    _validate_methods(plugin_base_class, plugin_impl)
    plugin_base_class.register(plugin_impl)


def register_plugin(plugin_base_class, plugin_abs_file_path):
    registered_plugins = []
    plugin_dir = os.path.dirname(os.path.realpath(plugin_abs_file_path))
    _register_plugin_path(plugin_dir)
    module_name = _get_plugin_module(plugin_abs_file_path)
    if module_name is None:
        return None
    module = importlib.import_module(module_name)
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
        raise Exception('Found no classes in plugin file ' + plugin_abs_file_path
                        + ' matching requirements.')

    return registered_plugins
