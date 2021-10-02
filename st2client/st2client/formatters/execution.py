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

import ast
import logging
import struct

import yaml

try:
    from yaml import CSafeDumper as YamlSafeDumper
except ImportError:
    # NOTE: We install libyaml-dev in our packages so libyaml will always be available when using
    # official StackStorm packages.
    # Only time it may not be available is if the user is doing custom install from source or
    # similar.
    logging.getLogger(__name__).warn(
        "libYAML C bindings are not available. This means YAML "
        "parsing and serialization will be significantly slower. You are "
        "strongly recommended to install libyaml (libyaml-dev package "
        "on Debian). For more information, see https://pyyaml.org/wiki/LibYAML"
    )
    from yaml import SafeDumper as YamlSafeDumper

from st2client import formatters
from st2client.config import get_config
from st2client.utils import jsutil
from st2client.utils import strutil
from st2client.utils.color import DisplayColors
from st2client.utils import schema
import six


LOG = logging.getLogger(__name__)

PLATFORM_MAXINT = 2 ** (struct.Struct("i").size * 8 - 1) - 1


def _print_bordered(text):
    lines = text.split("\n")
    width = max(len(s) for s in lines) + 2
    res = ["\n+" + "-" * width + "+"]
    for s in lines:
        res.append("| " + (s + " " * width)[: width - 2] + " |")
    res.append("+" + "-" * width + "+")
    return "\n".join(res)


class ExecutionResult(formatters.Formatter):
    @classmethod
    def format(cls, entry, *args, **kwargs):
        attrs = kwargs.get("attributes", [])
        attribute_transform_functions = kwargs.get("attribute_transform_functions", {})
        key = kwargs.get("key", None)
        if key:
            output = jsutil.get_value(entry.result, key)
        else:
            # drop entry to the dict so that jsutil can operate
            entry = vars(entry)
            output = ""
            for attr in attrs:
                value = jsutil.get_value(entry, attr)
                value = strutil.strip_carriage_returns(strutil.unescape(value))

                # transform the value of our attribute so things like 'status'
                # and 'timestamp' are formatted nicely
                transform_function = attribute_transform_functions.get(
                    attr, lambda value: value
                )
                value = transform_function(value=value)

                # TODO: This check is inherently flawed since it will crash st2client
                # if the leading character is objectish start and last character is objectish
                # end but the string isn't supposed to be a object. Try/Except will catch
                # this for now, but this should be improved.
                if (
                    isinstance(value, six.string_types)
                    and len(value) > 0
                    and value[0] in ["{", "["]
                    and value[len(value) - 1] in ["}", "]"]
                ):
                    try:
                        new_value = ast.literal_eval(value)
                    except:
                        new_value = value
                    if type(new_value) in [dict, list]:
                        value = new_value
                if isinstance(value, (dict, list)):
                    # 1. To get a nice overhang indent get safe_dump to generate output with
                    #    the attribute key and then remove the attribute key from the string.
                    # 2. Drop the trailing newline
                    # 3. Set width to maxint so pyyaml does not split text. Anything longer
                    #    and likely we will see other issues like storage :P.
                    # NOTE: We use C version of the safe dumper which is faster.
                    # Keep in mind that using YamlSafeDumper is the same as using yaml.safe_dumps
                    # (same class is used underneath when using yaml.safe_dump) so the code is safe.
                    formatted_value = yaml.dump(
                        {attr: value},
                        default_flow_style=False,
                        width=PLATFORM_MAXINT,
                        indent=2,
                        Dumper=YamlSafeDumper,
                    )[len(attr) + 2 : -1]

                    if isinstance(value, list):
                        # Indent list values with 2 spaces for a nicer display.
                        lines = formatted_value.split("\n")
                        formatted_value = []
                        for line in lines:
                            formatted_value.append("  %s" % (line))

                        formatted_value = "\n".join(formatted_value)

                    value = (
                        "\n" if isinstance(value, (dict, list)) else ""
                    ) + formatted_value
                    value = strutil.dedupe_newlines(value)

                # transform the value of our attribute so things like 'status'
                # and 'timestamp' are formatted nicely
                transform_function = attribute_transform_functions.get(
                    attr, lambda value: value
                )
                value = transform_function(value=value)

                output += ("\n" if output else "") + "%s: %s" % (
                    DisplayColors.colorize(attr, DisplayColors.BLUE),
                    value,
                )

            output_schema = entry.get("action", {}).get("output_schema")
            schema_check = get_config()["general"]["silence_schema_output"]
            if not output_schema and kwargs.get("with_schema"):
                rendered_schema = {
                    "output_schema": schema.render_output_schema_from_output(
                        entry["result"]
                    )
                }

                rendered_schema = yaml.safe_dump(
                    rendered_schema, default_flow_style=False
                )
                output += "\n"
                output += _print_bordered(
                    "Based on the action output the following inferred schema was built:"
                    "\n\n"
                    "%s" % rendered_schema
                )
            elif not output_schema and not schema_check:
                output += (
                    "\n\n** This action does not have an output_schema. "
                    "Run again with --with-schema to see a suggested schema."
                )

        if six.PY3:
            return strutil.unescape(str(output))
        else:
            # Assume Python 2
            try:
                result = (
                    strutil.unescape(str(output))
                    .decode("unicode_escape")
                    .encode("utf-8")
                )
            except UnicodeDecodeError:
                # String contains a value which is not an unicode escape sequence, ignore the error
                result = strutil.unescape(str(output))
            return result
