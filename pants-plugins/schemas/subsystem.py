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


class GenerateSchemas(Subsystem):
    name = "StackStorm Content Schemas Generator"
    options_scope = "st2-generate-schemas"
    skip = SkipOption("fmt", "lint")
    help = "The StackStorm content schemas generator."

    source_root = "st2common"
    directory = "st2common/st2common/cmd"
    module = "st2common.cmd"
    cmd = "generate_schemas"

    def address(self) -> Address:
        return Address(
            self.directory,
            target_name="cmd",
            relative_file_path=f"{self.cmd}.py",
        )

    def pex_request(self) -> PexFromTargetsRequest:
        return PexFromTargetsRequest(
            [self.address()],
            output_filename=f"{self.cmd}.pex",
            internal_only=True,
            main=EntryPoint.parse(f"{self.module}.{self.cmd}:main"),
        )
