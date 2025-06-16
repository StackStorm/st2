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

import logging

import yaml

try:
    from yaml import CSafeLoader as YamlSafeLoader
    from yaml import CSafeDumper as YamlSafeDumper
except ImportError:
    # NOTE: We install libyaml-dev in our packages so libyaml will always be available when using
    # official StackStorm packages.
    # Only time it may not be available is if the user is doing custom install from source or
    # similar.
    logging.getLogger(__name__).warning(
        "libYAML C bindings are not available. This means YAML "
        "parsing and serialization will be significantly slower. You are "
        "strongly recommended to install libyaml (libyaml-dev package "
        "on Debian). For more information, see https://pyyaml.org/wiki/LibYAML"
    )
    from yaml import SafeLoader as YamlSafeLoader
    from yaml import SafeDumper as YamlSafeDumper

__all__ = ["ALLOWED_EXTS", "PARSER_FUNCS"]


# NOTE: We utilize CSafeLoader if available since it uses C extensions and is faster.
#
# SafeLoader / CSafeLoader are both safe to use and don't allow loading arbitrary Python objects.
#
# That's the actual class which is used internally by ``yaml.safe_load()``, but we can't use that
# method directly since we want to use C extension if available (CSafeLoader) for faster parsing.
#
# Same goes for dumper class.
#
# See pyyaml docs for details https://pyyaml.org/wiki/PyYAMLDocumentation
def yaml_safe_load(stream):
    return yaml.load(stream, Loader=YamlSafeLoader)


def yaml_safe_dump(data, **kwargs):
    return yaml.dump(data, Dumper=YamlSafeDumper, **kwargs)


ALLOWED_EXTS = [".yaml", ".yml"]
PARSER_FUNCS = {".yml": yaml_safe_load, ".yaml": yaml_safe_load}
