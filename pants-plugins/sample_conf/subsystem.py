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
from pants.backend.python.target_types import EntryPoint
from pants.backend.python.util_rules.pex_from_targets import PexFromTargetsRequest
from pants.engine.addresses import Address
from pants.option.option_types import SkipOption
from pants.option.subsystem import Subsystem


class ConfigGen(Subsystem):
    name = "StackStorm Sample st2.conf Generator"
    options_scope = "st2-config-gen"
    skip = SkipOption("fmt", "lint")
    help = "The StackStorm st2.conf.sample generator."

    directory = "tools"
    script = "config_gen"

    def address(self) -> Address:
        return Address(
            self.directory,
            target_name=self.directory,
            relative_file_path=f"{self.script}.py",
        )

    def pex_request(self) -> PexFromTargetsRequest:
        return PexFromTargetsRequest(
            [self.address()],
            output_filename=f"{self.script}.pex",
            internal_only=True,
            main=EntryPoint(self.script),
        )
