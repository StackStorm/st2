# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
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

from st2common.util.monkey_patch import monkey_patch

# Note: We need to perform monkey patching in the worker. If we do it in
# the master process (gunicorn_config.py), it breaks tons of things
# including shutdown
# NOTE: It's important that we perform monkey patch as early as possible before any other modules
# are important, otherwise SSL support for MongoDB won't work.
# See https://github.com/StackStorm/st2/issues/4832 and https://github.com/gevent/gevent/issues/1016
# for details.
monkey_patch()

from st2auth import app

config = {
    "is_gunicorn": True,
    "config_args": [
        "--config-file",
        os.environ.get("ST2_CONFIG_PATH", "/etc/st2/st2.conf"),
    ],
}

application = app.setup_app(config)
