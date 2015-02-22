# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Script which generates documentation section which contains information about
available runner parameters.
"""

import argparse

from st2actions.bootstrap.runnersregistrar import RUNNER_TYPES


def main(name):
    result = []

    runner = [runner for runner in RUNNER_TYPES if runner['name'] == name][0]

    result.append('Runner parameters')
    result.append('~~~~~~~~~~~~~~~~~')
    result.append('')

    for name, values in runner['runner_parameters'].items():
        format_values = {'name': name}
        format_values.update(values)
        line = '* ``%(name)s`` (%(type)s) - %(description)s' % format_values
        result.append(line)

    result = '\n'.join(result)
    print(result)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Runner parameter documentation generation')
    parser.add_argument('--name', required=True,
                        help='Name of the runner to generate the documentation for')
    args = parser.parse_args()

    main(name=args.name)
