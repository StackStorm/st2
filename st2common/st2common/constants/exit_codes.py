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

__all__ = [
    "SUCCESS_EXIT_CODE",
    "FAILURE_EXIT_CODE",
    "SIGKILL_EXIT_CODE",
    "SIGTERM_EXIT_CODE",
]

SUCCESS_EXIT_CODE = 0
FAILURE_EXIT_CODE = 1
SIGKILL_EXIT_CODE = 9
SIGTERM_EXIT_CODE = 15
