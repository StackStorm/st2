# coding: utf-8
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Mapping, Tuple

from pants.backend.python.target_types import PythonTests, PythonTestsDependencies
from pants.base.specs import AddressSpecs, DescendantAddresses
from pants.engine.addresses import Address
from pants.engine.rules import collect_rules, Get, MultiGet, rule, UnionRule
from pants.engine.target import (
    InjectDependenciesRequest,
    InjectedDependencies,
    StringSequenceField,
    Targets,
    WrappedTarget,
)
from pants.util.frozendict import FrozenDict
from pants.util.logging import LogLevel
from pants.util.ordered_set import FrozenOrderedSet, OrderedSet

from stevedore_extensions.target_types import (
    StevedoreExtension,
    StevedoreNamespaceField,
    StevedoreSources,
)


@dataclass(frozen=True)
class StevedoreExtensions:
    """A mapping of stevedore namespaces to a list the targets that provide them"""
    mapping: FrozenDict[str, Tuple[StevedoreExtension]]


# This is a lot like a SpecialCasedDependencies field, but it doesn't list targets directly.
class StevedoreNamespacesField(StringSequenceField):
    alias = "stevedore_namespaces"
    help = (
        "A list of stevedore namespaces to include for tests.\n\n"
        "All stevedore_extension targets with these namespaces will be added as "
        "dependencies so that they are available on PYTHONPATH during tests. "
        "The stevedore namespace format (my.stevedore.extension) is similar "
        "to a python namespace."
    )


@rule(desc="Creating map of stevedore_extension namespaces to StevedoreExtension targets", level=LogLevel.DEBUG)
async def map_stevedore_extensions() -> StevedoreExtensions:
    all_expanded_targets = await Get(Targets, AddressSpecs([DescendantAddresses("")]))
    stevedore_extensions = tuple(tgt for tgt in all_expanded_targets if tgt.has_field(StevedoreSources))
    mapping: Mapping[str, List[StevedoreExtension]] = defaultdict(list)
    for extension in stevedore_extensions:
        mapping[extension[StevedoreNamespaceField].value].append(extension)
    return StevedoreExtensions(
        FrozenDict(
            (k, tuple(v)) for k, v in sorted(mapping.items())
        )
    )


class InjectStevedoreNamespaceDependencies(InjectDependenciesRequest):
    inject_for = PythonTestsDependencies


@rule(desc="Inject stevedore_extension target dependencies for python_tests based on namespace list.")
async def inject_stevedore_dependencies(
    request: InjectStevedoreNamespaceDependencies, stevedore_extensions: StevedoreExtensions
) -> InjectedDependencies:
    original_tgt: WrappedTarget
    original_tgt = await Get(WrappedTarget, Address, request.dependencies_field.address)
    if original_tgt.target.get(StevedoreNamespacesField).value is None:
        return InjectedDependencies()

    namespaces: StevedoreNamespacesField = original_tgt.target[StevedoreNamespacesField]

    addresses = []
    for namespace in namespaces.value:
        extensions = stevedore_extensions.mapping.get(namespace, ())
        addresses.extend(extension.address for extension in extensions)

    result: OrderedSet[Address] = OrderedSet(addresses)
    return InjectedDependencies(sorted(result))


def rules():
    return [
        *collect_rules(),
        PythonTests.register_plugin_field(StevedoreNamespacesField),
        UnionRule(InjectDependenciesRequest, InjectStevedoreNamespaceDependencies),
    ]
