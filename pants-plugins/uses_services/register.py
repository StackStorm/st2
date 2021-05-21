from uses_services import mongo, platform_, target_types


def rules():
    return [
        *target_types.rules(),
        *platform_.rules(),
        *mongo.rules(),
    ]
