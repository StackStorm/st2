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

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import os

from st2stream import app

config = {
    "is_gunicorn": True,
    "config_args": [
        "--config-file",
        os.environ.get("ST2_CONFIG_PATH", "/etc/st2/st2.conf"),
    ],
}

application = app.setup_app(config)
