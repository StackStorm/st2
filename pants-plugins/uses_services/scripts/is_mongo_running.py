# Copyright 2021 The StackStorm Authors.
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
import sys


def _is_mongo_running(
    db_host: str, db_port: int, db_name: str, connection_timeout_ms: int
) -> bool:
    # late import so that __file__ can be imported in the pants plugin without these imports
    import mongoengine
    from pymongo.errors import ConnectionFailure
    from pymongo.errors import ServerSelectionTimeoutError

    # cf st2common.models.db.setup()
    connection = mongoengine.connection.connect(
        db_name,
        host=db_host,
        port=db_port,
        connectTimeoutMS=connection_timeout_ms,
        serverSelectionTimeoutMS=connection_timeout_ms,
    )

    # connection.connect() is lazy. Make a command to test connection.
    try:
        # The ismaster command is cheap and does not require auth
        connection.admin.command("ismaster")
    except (ConnectionFailure, ServerSelectionTimeoutError):
        return False
    return True


if __name__ == "__main__":
    args = dict((k, v) for k, v in enumerate(sys.argv))
    db_host = args.get(1, "127.0.0.1")
    db_port = args.get(2, 27017)
    db_name = args.get(3, "st2-test")
    connection_timeout_ms = args.get(4, 3000)

    is_running = _is_mongo_running(
        db_host, int(db_port), db_name, int(connection_timeout_ms)
    )
    exit_code = 0 if is_running else 1
    sys.exit(exit_code)
