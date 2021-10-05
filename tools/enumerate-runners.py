#!/usr/bin/env python
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

from __future__ import absolute_import

from st2common.runners import get_available_backends
from st2common.runners import get_backend_driver

from st2common import config

config.parse_args()

runner_names = get_available_backends()

print("Available / installed action runners:")
for name in runner_names:
    runner_driver = get_backend_driver(name)
    runner_instance = runner_driver.get_runner()
    runner_metadata = runner_driver.get_metadata()

    print(
        "- %s (runner_module=%s,cls=%s)"
        % (name, runner_metadata["runner_module"], runner_instance.__class__)
    )
