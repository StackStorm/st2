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
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Mapping, Tuple

from pants.backend.python.target_types import (
    PythonTestTarget,
    PythonTestsGeneratorTarget,
    PythonTestsDependenciesField,
)
from pants.engine.addresses import Address
from pants.engine.rules import collect_rules, rule, UnionRule
from pants.engine.target import (
    AllTargets,
    FieldSet,
    InferDependenciesRequest,
    InferredDependencies,
)
from pants.util.frozendict import FrozenDict
from pants.util.logging import LogLevel
from pants.util.ordered_set import OrderedSet

from stevedore_extensions.target_types import (
    AllStevedoreExtensionTargets,
    StevedoreEntryPointsField,
    StevedoreExtension,
    StevedoreNamespaceField,
    StevedoreNamespacesField,
)


# -----------------------------------------------------------------------------------------------
# Utility rules to analyze all `StevedoreExtension` targets
# -----------------------------------------------------------------------------------------------


@rule(desc="Find all StevedoreExtension targets in project", level=LogLevel.DEBUG)
def find_all_stevedore_extension_targets(
    targets: AllTargets,
) -> AllStevedoreExtensionTargets:
    return AllStevedoreExtensionTargets(
        tgt for tgt in targets if tgt.has_field(StevedoreEntryPointsField)
    )


@dataclass(frozen=True)
class StevedoreExtensions:
    """A mapping of stevedore namespaces to a list the targets that provide them"""

    mapping: FrozenDict[str, Tuple[StevedoreExtension]]


@rule(
    desc="Creating map of stevedore_extension namespaces to StevedoreExtension targets",
    level=LogLevel.DEBUG,
)
async def map_stevedore_extensions(
    stevedore_extensions: AllStevedoreExtensionTargets,
) -> StevedoreExtensions:
    mapping: Mapping[str, List[StevedoreExtension]] = defaultdict(list)
    for extension in stevedore_extensions:
        mapping[extension[StevedoreNamespaceField].value].append(extension)
    return StevedoreExtensions(
        FrozenDict((k, tuple(v)) for k, v in sorted(mapping.items()))
    )


# -----------------------------------------------------------------------------------------------
# Dependencies for `python_test` and `python_tests` targets
# -----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PythonTestsStevedoreNamespaceInferenceFieldSet(FieldSet):
    required_fields = (PythonTestsDependenciesField, StevedoreNamespacesField)

    stevedore_namespaces: StevedoreNamespacesField


class InferStevedoreNamespaceDependencies(InferDependenciesRequest):
    infer_from = PythonTestsStevedoreNamespaceInferenceFieldSet


@rule(
    desc="Infer stevedore_extension target dependencies based on namespace list.",
    level=LogLevel.DEBUG,
)
async def infer_stevedore_namespace_dependencies(
    request: InferStevedoreNamespaceDependencies,
    stevedore_extensions: StevedoreExtensions,
) -> InferredDependencies:
    namespaces: StevedoreNamespacesField = request.field_set.stevedore_namespaces
    if namespaces.value is None:
        return InferredDependencies(())

    addresses = []
    for namespace in namespaces.value:
        extensions = stevedore_extensions.mapping.get(namespace, ())
        addresses.extend(extension.address for extension in extensions)

    result: OrderedSet[Address] = OrderedSet(addresses)
    return InferredDependencies(sorted(result))


def rules():
    return [
        *collect_rules(),
        PythonTestsGeneratorTarget.register_plugin_field(StevedoreNamespacesField),
        PythonTestTarget.register_plugin_field(StevedoreNamespacesField),
        UnionRule(InferDependenciesRequest, InferStevedoreNamespaceDependencies),
    ]
