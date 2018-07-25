#!/usr/bin/env bash
# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# 1. Install codecov dependencies
# NOTE: We need eventlet installed so coverage can be correctly combined. This is needed because we are covering code which utilizes eventlet.
# Without eventlet being available to the coverage command it will fail with "Couldn't trace with concurrency=eventlet, the module isn't installed."
pip install eventlet
pip install -e "git+https://github.com/StackStorm/codecov-python.git@better_error_output#egg=codecov"

# 2. Combine coverage report and submit coverage report to codecovs.io
codecov --required
