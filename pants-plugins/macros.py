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


def st2_shell_sources_and_resources(**kwargs):
    """This creates a shell_sources and a resources target.

    This is needed because python_sources dependencies on shell_sources
    are silently ignored. So, we also need the resources target
    to allow depending on them.
    """
    shell_sources(**kwargs)

    kwargs.pop("skip_shellcheck")

    kwargs["name"] += "_resources"
    resources(**kwargs)
