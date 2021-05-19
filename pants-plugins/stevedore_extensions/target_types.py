# coding: utf-8
# repurposed from pants.backend.python.target_types
import os

from dataclasses import dataclass
from typing import Dict, Optional

from pants.engine.addresses import Address
from pants.engine.collection import Collection
from pants.engine.target import (
    AsyncFieldMixin,
    COMMON_TARGET_FIELDS,
    Dependencies,
    DictStringToStringField,
    InvalidFieldException,
    SecondaryOwnerMixin,
    Sources,
    StringField,
    Target,
)
from pants.backend.python.target_types import EntryPoint
from pants.source.filespec import Filespec


@dataclass(frozen=True)
class StevedoreEntryPoint:
    name: str
    value: EntryPoint


class StevedoreEntryPoints(Collection[StevedoreEntryPoint]):
    pass


class StevedoreNamespaceField(StringField):
    alias = "namespace"
    help = (
        "The stevedore extension namespace.\n\nThis looks like a python module "
        "'my.stevedore.namespace', but a python module of that name does not "
        "need to exist. This is what a stevedore ExtensionManager uses to look up "
        "relevant entry_points from pkg_resources."
    )
    required = True


class StevedoreEntryPointsField(AsyncFieldMixin, SecondaryOwnerMixin, DictStringToStringField):
    # based on pants.backend.python.target_types.PexEntryPointField
    alias = "entry_points"
    help = (
        "A dict that maps a stevedore extension name to the entry_point that implements it.\n\n"
        # the odd spacing here minimizes diff with help text copied from PexEntryPointField
        "You can specify each entry_point with "
        "a full module like 'path.to.module' and 'path.to.module:func', or use a "
        "shorthand to specify a file name, using the same syntax as the `sources` field:\n\n  1) "
        "'app.py', Pants will convert into the module `path.to.app`;\n  2) 'app.py:func', Pants "
        "will convert into `path.to.app:func`.\n\nYou must use the file name shorthand for file "
        "arguments to work with this target."
    )
    required = True
    value: StevedoreEntryPoints

    @classmethod
    def compute_value(cls, raw_value: Optional[Dict[str, str]], address: Address) -> Collection[StevedoreEntryPoint]:
        # TODO: maybe support raw entry point maps like ["name = path.to.module:func"]
        #       raw_value: Optional[Union[Dict[str, str], List[str]]]
        raw_entry_points = super().compute_value(raw_value, address)
        entry_points = []
        for name, value in raw_entry_points.items():
            try:
                entry_point = EntryPoint.parse(value)
            except ValueError as e:
                raise InvalidFieldException(str(e))
            entry_points.append(StevedoreEntryPoint(name=name, value=entry_point))
        return StevedoreEntryPoints(entry_points)

    @property
    def filespec(self) -> Filespec:
        includes = []
        for entry_point in self.value:
            if not entry_point.value.module.endswith(".py"):
                continue
            full_glob = os.path.join(self.address.spec_path, entry_point.value.module)
            includes.append(full_glob)
        return {"includes": includes}


# See `target_types_rules.py` for the `ResolveStevedoreEntryPointsRequest -> ResolvedStevedoreEntryPoints` rule.
@dataclass(frozen=True)
class ResolvedStevedoreEntryPoints:
    val: Optional[StevedoreEntryPoints]


@dataclass(frozen=True)
class ResolveStevedoreEntryPointsRequest:
    """Determine the `entry_points` for a `stevedore_extension` after applying all syntactic sugar."""

    entry_points_field: StevedoreEntryPointsField


# See `target_types_rules.py` for a dependency injection rule.
class StevedoreDependencies(Dependencies):
    # dummy field for dependency injection to work
    alias = "_stevedore_dependencies"


# based on pants.core.target_types.RelocatedFilesSources
class StevedoreSources(Sources):
    # dummy field for codegen to work
    alias = "_stevedore_sources"
    expected_num_files = 0


class StevedoreExtension(Target):
    alias = "stevedore_extension"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        StevedoreNamespaceField,
        StevedoreEntryPointsField,
        StevedoreSources,
        StevedoreDependencies,
    )
    help = f"Entry points used to generate setuptools metadata for stevedore."


