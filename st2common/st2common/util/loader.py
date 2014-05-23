import os
import sys
import importlib

FACTORY_IDENTIFIER = 'get_plugin'
PYTHON_EXTENSIONS = ('.py', '.pyc')


def __update_python_path(module_path):
    if not module_path or module_path in sys.path:
        return
    # generate absolute module path prior to addition
    abs_module_path = os.path.abspath(module_path)
    sys.path.append(abs_module_path)


def __get_plugin_factory(plugin_module):
    module = importlib.import_module(plugin_module)
    factory = getattr(module, FACTORY_IDENTIFIER)
    return factory


def get_plugin_factory_m(plugin_module, module_path=None):
    """
    Returns the factory that can used to construct a plugin found in the
    supplied module. The contract between the callable factory and consumer
    is opaque to this implementation.

    System layout example.
        package layout ->
            package-root/
                plugin/
                    impl/
                        plugin_module.py
                    util/
                        utility.py

        content of plugin_module.py ->
            from plugin.util import utility
            ...

    Consumption e.g. ->
        factory = get_plugin_factory_m('plugin.impl.plugin_module',
                                       'package-root')
        # construct_spec is essentially the opaque contract.
        construct_spec = {'arg1':'v1', 'arg2':'v2'}
        plugin_instance = factory(**construct_spec)

    :param plugin_module: name of the plugin module. The module name should
    be qualified with a package name accessible from the python path.
    :param module_path: path to import from the file system to satisfy
    module dependencies. If none is provided the assumption is the module
    already exist on the python path.
    :return: callable factory to instantiate the plugin.
    """
    __update_python_path(module_path)
    return __get_plugin_factory(plugin_module)


def get_plugin_factory_f(plugin_module_file):
    """
    Returns the factory that can used to construct a plugin found in the
    module represented by the supplied file.
    The contract between the callable factory and consumer is opaque to this
    implementation.
    :param plugin_module_file: path to the file. Typical rules of fully
    qualified paths and relative paths apply.
    :return: callable factory to instantiate the plugin.
    """
    plugin_module = os.path.basename(plugin_module_file)
    if plugin_module.endswith(PYTHON_EXTENSIONS):
        plugin_module = plugin_module[:plugin_module.rfind('.py')]
    return get_plugin_factory_m(plugin_module,
                                os.path.dirname(plugin_module_file))
