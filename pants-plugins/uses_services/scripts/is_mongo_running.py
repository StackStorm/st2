# Copyright 2023 The StackStorm Authors.
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
import os
import sys


def _is_mongo_running(
    db_host: str, db_port: int, db_name: str, connection_timeout_ms: int
) -> bool:
    """Connect to mongo with connection logic that mirrors the st2 code.

    In particular, this is based on st2common.models.db.db_setup().
    This should not import the st2 code as it should be self-contained.
    """
    # late import so that __file__ can be imported in the pants plugin without these imports
    import mongoengine
    from pymongo.errors import ConnectionFailure
    from pymongo.errors import ServerSelectionTimeoutError

    connection = mongoengine.connection.connect(
        db_name,
        host=db_host,
        port=db_port,
        connectTimeoutMS=connection_timeout_ms,
        serverSelectionTimeoutMS=connection_timeout_ms,
        uuidRepresentation="pythonLegacy",
    )

    # connection.connect() is lazy. Make a command to test the connection.
    try:
        # The ping command is cheap and does not require auth
        # https://www.mongodb.com/community/forums/t/how-to-use-the-new-hello-interface-for-availability/116748/
        connection.admin.command("ping")
    except (ConnectionFailure, ServerSelectionTimeoutError):
        return False
    return True


if __name__ == "__main__":
    args = dict((k, v) for k, v in enumerate(sys.argv))
    db_host = args.get(1, "127.0.0.1")
    db_port = args.get(2, 27017)
    db_name = args.get(3, "st2-test{}")
    connection_timeout_ms = args.get(4, 3000)

    slot_var = os.environ.get(
        "PANTS_PYTEST_EXECUTION_SLOT_VAR", "ST2TESTS_PARALLEL_SLOT"
    )
    db_name = db_name.format(os.environ.get(slot_var) or "")

    is_running = _is_mongo_running(
        db_host, int(db_port), db_name, int(connection_timeout_ms)
    )
    exit_code = 0 if is_running else 1
    sys.exit(exit_code)
