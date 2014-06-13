import importlib
import inspect
import os
import sys

from st2common import log as logging


LOG = logging.getLogger(__name__)
PYTHON_EXTENSIONS = ('.py')


def __register_plugin_path(plugin_dir_abs_path):
    if not os.path.isdir(plugin_dir_abs_path):
        raise Exception('Directory containing plugins must be provided.')
    for x in sys.path:
        if plugin_dir_abs_path in (x, x + os.sep):
            return
    sys.path.append(plugin_dir_abs_path)


def __get_plugin_module(plugin_file_path):
    plugin_module = os.path.basename(plugin_file_path)
    if plugin_module.endswith(PYTHON_EXTENSIONS):
        plugin_module = plugin_module[:plugin_module.rfind('.py')]
    else:
        plugin_module = None
    return plugin_module


def __get_classes_in_module(module):
    classes = []
    for name, kls in inspect.getmembers(module):
        if inspect.isclass(kls):
            classes.append(kls)
    return classes


def __get_plugin_classes(module_name):
    return __get_classes_in_module(module_name)


def __get_plugin_methods(plugin_klass):
    plugin_methods = []
    for name, method in inspect.getmembers(plugin_klass):
        if inspect.ismethod(method):
            plugin_methods.append(name)
    return plugin_methods


def __validate_methods(plugin_base_class, plugin_klass):
    '''
    XXX: This is hacky but we'd like to validate the methods
    in plugin_impl at least has all the *abstract* methods in
    plugin_base_class.
    '''
    expected_methods = plugin_base_class.__abstractmethods__
    plugin_methods = __get_plugin_methods(plugin_klass)
    for method in expected_methods:
        if method not in plugin_methods:
            raise Exception('Class %s does not implement method %s in base class.'
                            % (plugin_klass, method))


def __register_plugin(plugin_base_class, plugin_impl):
    __validate_methods(plugin_base_class, plugin_impl)
    plugin_base_class.register(plugin_impl)


def register_plugin(plugin_base_class, plugin_abs_file_path):
    registered_plugins = []
    plugin_dir = os.path.dirname(os.path.realpath(plugin_abs_file_path))
    __register_plugin_path(plugin_dir)
    module_name = __get_plugin_module(plugin_abs_file_path)
    if module_name is None:
        return instances
    module = importlib.import_module(module_name)
    klasses = __get_plugin_classes(module)

    # Try registering classes in plugin file. Some may fail.
    for klass in klasses:
        try:
            __register_plugin(plugin_base_class, klass)
            registered_plugins.append(klass)
        except Exception, e:
            LOG.exception(e)
            LOG.debug('Skipping class %s as it doesn\'t match specs.', klass)
            continue

    if len(registered_plugins) == 0:
        raise Exception('Found no classes in plugin file ' + plugin_abs_file_path
                        + ' matching requirements.')

    return registered_plugins

