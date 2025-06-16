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

"""
A script generates final openapi.yaml file based on openapi.yaml.j2 Jinja
template file.
"""

from __future__ import absolute_import
from st2common import config
from st2common import log as logging
from st2common.util import spec_loader
from st2common.script_setup import setup as common_setup
from st2common.script_setup import teardown as common_teardown

__all__ = ["main"]

LOG = logging.getLogger(__name__)


# TODO: replace makefile reference with pants equivalent
# pants fmt st2common/st2common/openapi.yaml
SPEC_HEADER = """\
# NOTE: This file is auto-generated - DO NOT EDIT MANUALLY
# Edit st2common/st2common/openapi.yaml.j2 and then run
# make .generate-api-spec
# to generate the final spec file
"""


def setup():
    common_setup(config=config, setup_db=False, register_mq_exchanges=False)


def generate_spec():
    spec_string = spec_loader.generate_spec("st2common", "openapi.yaml.j2")
    print(SPEC_HEADER.rstrip())
    print(spec_string)


def teartown():
    common_teardown()


def main():
    setup()

    try:
        generate_spec()
        ret = 0
    except Exception:
        LOG.error("Failed to generate openapi.yaml file", exc_info=True)
        ret = 1
    finally:
        teartown()

    return ret
