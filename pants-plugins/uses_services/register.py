from pants.backend.python.target_types import PythonTests

from . import mongo
from . import platform_
from .uses_services import UsesServicesField


def rules():
    return [
        PythonTests.register_plugin_field(UsesServicesField),
        *platform_.rules(),
        *mongo.rules(),
    ]
