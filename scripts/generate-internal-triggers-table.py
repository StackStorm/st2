#!/usr/bin/env python
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
Script which generates a table with system triggers which is included in the
documentation.
"""

import os

from st2common.constants.triggers import INTERNAL_TRIGGER_TYPES

from utils import as_rest_table

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    lines = []

    for resource_type, trigger_definitions in INTERNAL_TRIGGER_TYPES.items():
        resource_title = resource_type.title().replace('_', ' ')
        lines.append(resource_title)
        lines.append('~' * (len(resource_title)))
        lines.append('')

        rows = []
        rows.append(['Reference', 'Description', 'Properties'])

        for trigger_definition in trigger_definitions:
            properties = trigger_definition['payload_schema']['properties'].keys()
            properties = ', '.join(properties)
            row = [trigger_definition['name'], trigger_definition['description'], properties]
            rows.append(row)

        table = as_rest_table(rows, full=True)
        lines.extend(table.split('\n'))
        lines.append('')

    result = '\n'.join(lines)

    destination_path = os.path.join(CURRENT_DIR, '../docs/source/_includes/internal_trigger_types.rst')
    with open(destination_path, 'w') as fp:
        fp.write(result)

    print('Generated: %s' % (destination_path))
    return result


if __name__ == '__main__':
    main()
