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

# If we're on GitHub Actions (eg: the user is 'runner'), then the workflow
# has already checked that the build has succeeded.
# If we're on Travis, then we need to manually check that the build succeeded.
if [[ "${USER}" == "runner" || ${TRAVIS_TEST_RESULT} -eq 0 ]]; then
    # 1. Install codecov dependencies
    # NOTE: We need eventlet installed so coverage can be correctly combined. This is needed because we are covering code which utilizes eventlet.
    # Without eventlet being available to the coverage command it will fail with "Couldn't trace with concurrency=eventlet, the module isn't installed."
    pip install eventlet
    # NOTE: codecov only supports coverage==4.5.2
    pip install 'coverage<5.0'
    pip install "codecov==2.1.11"

    # 2. Combine coverage report and submit coverage report to codecovs.io
    codecov --required
    exit $?
else
    echo "Build has failed, not submitting coverage"
    exit 0
fi
