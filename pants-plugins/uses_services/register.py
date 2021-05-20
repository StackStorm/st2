from uses_services import mongo, platform_, uses_services


def rules():
    return [
        *uses_services.rules(),
        *platform_.rules(),
        *mongo.rules(),
    ]
