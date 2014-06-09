import importlib
import inspect
import logging
import os
import sys

LOG = logging.getLogger(__name__)
PYTHON_EXTENSIONS = ('.py')


def __register_plugin_path(plugin_dir_abs_path):
    if not os.path.isdir(plugin_dir_abs_path):
        raise Exception('Directory containing sensor must be provided.')
    for x in sys.path:
        if plugin_dir_abs_path in (x, x + os.sep):
            return
    sys.path.append(plugin_dir_abs_path)


def __get_plugin_module(plugin_file_path):
    plugin_module = os.path.basename(plugin_file_path)
    if plugin_module.endswith(PYTHON_EXTENSIONS):
        plugin_module = plugin_module[:plugin_module.rfind('.py')]
    return plugin_module


def __get_classes_in_module(module):
    classes = []
    for name, cls in inspect.getmembers(module):
        if inspect.isclass(cls):
            classes.append(cls)
    return classes


def __get_plugin_classes(module_name):
    return __get_classes_in_module(module_name)


def __register_plugin(plugin_base_class, plugin_instance):
    plugin_base_class.register(plugin_instance)


def register_plugin(plugin_base_class, plugin_abs_file_path):
    instances = []
    plugin_dir = os.path.dirname(os.path.realpath(plugin_abs_file_path))
    __register_plugin_path(plugin_dir)
    module_name = __get_plugin_module(plugin_abs_file_path)
    module = importlib.import_module(module_name)
    klasses = __get_plugin_classes(module)

    # Try registering classes in plugin file. Some may fail.
    for klass in klasses:
        try:
            __register_plugin(plugin_base_class, klass)
            instances.append(klass())
        except:
            LOG.debug('Skipping class %s as it doesn\'t match specs.', klass)
            continue

    if len(instances) == 0:
        raise Exception('Found no classes in plugin file' +
                        ' matching requirements.')

    return instances

