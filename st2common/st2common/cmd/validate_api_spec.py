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
A script that validates each entry defined in OpenAPI-Spec for st2 APIs
(in st2common/openapi.yaml) has a corresponding API model class defined
in st2common/models/api/.
"""

from __future__ import absolute_import
import os

import prance
from oslo_config import cfg

from st2common import config
from st2common import log as logging
from st2common.util import spec_loader
from st2common.script_setup import setup as common_setup
from st2common.script_setup import teardown as common_teardown
import six


__all__ = ["main"]


cfg.CONF.register_cli_opt(
    cfg.StrOpt(
        "spec-file",
        short="f",
        required=False,
        default="st2common/st2common/openapi.yaml",
    )
)

# When disabled, only load the spec in prance to validate. Otherwise check for x-api-model as well.
# validate-defs is disabled by default until these are resolved:
#   https://github.com/StackStorm/st2/issues/3575
#   https://github.com/StackStorm/st2/issues/3788
cfg.CONF.register_cli_opt(
    cfg.BoolOpt("validate-defs", short="-d", required=False, default=False)
)

cfg.CONF.register_cli_opt(
    cfg.BoolOpt("generate", short="-c", required=False, default=False)
)

LOG = logging.getLogger(__name__)


def setup():
    common_setup(config=config, setup_db=False, register_mq_exchanges=False)


def _validate_definitions(spec):
    defs = spec.get("definitions", None)
    error = False
    verbose = cfg.CONF.verbose

    for (model, definition) in six.iteritems(defs):
        api_model = definition.get("x-api-model", None)

        if not api_model:
            msg = (
                'API model field "x-api-model" not defined for definition "%s".' % model
            )

            if verbose:
                LOG.info("Supplied definition for model %s: \n\n%s.", model, definition)
                msg += "\n"

            error = True
            LOG.error(msg)

    return error


def validate_spec():
    spec_file = cfg.CONF.spec_file
    generate_spec = cfg.CONF.generate
    validate_defs = cfg.CONF.validate_defs

    if not os.path.exists(spec_file) and not generate_spec:
        msg = (
            "No spec file found in location %s. " % spec_file
            + "Provide a valid spec file or "
            + "pass --generate-api-spec to genrate a spec."
        )
        raise Exception(msg)

    if generate_spec:
        if not spec_file:
            raise Exception("Supply a path to write to spec file to.")

        spec_string = spec_loader.generate_spec("st2common", "openapi.yaml.j2")

        with open(spec_file, "w") as f:
            f.write(spec_string)
            f.flush()

    parser = prance.ResolvingParser(spec_file)
    spec = parser.specification

    if not validate_defs:
        return True

    return _validate_definitions(spec)


def teardown():
    common_teardown()


def main():
    setup()

    try:
        # Validate there are no duplicates keys in the YAML file.
        # The spec loader do not allow duplicate keys.
        spec_loader.load_spec("st2common", "openapi.yaml.j2")

        # run the schema through prance to validate openapi spec.
        passed = validate_spec()

        ret = 0 if passed else 1
    except Exception:
        LOG.error("Failed to validate openapi.yaml file", exc_info=True)
        ret = 1
    finally:
        teardown()

    return ret
