from pants.backend.python.target_types import PythonTests

from uses_services import mongo, platform_
from uses_services.target_types import UsesServicesField


def rules():
    return [
        PythonTests.register_plugin_field(UsesServicesField),
        *platform_.rules(),
        *mongo.rules(),
    ]
