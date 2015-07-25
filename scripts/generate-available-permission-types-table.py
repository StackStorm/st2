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
Script which generates a table with the available permission types.
"""

import os

from st2common.rbac.types import ResourceType
from st2common.rbac.types import PermissionType

from utils import as_rest_table

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DESTINATION_PATH = os.path.join(CURRENT_DIR,
                                '../docs/source/_includes/available_permission_types.rst')
HEADER = '.. NOTE: This file has been generated automatically, don\'t manually edit it'
TABLE_HEADER = ['Permission name', 'Description']


def main():
    lines = []
    lines.append(HEADER)
    lines.append('')

    for resource_type in ResourceType.get_valid_values():
        resource_title = resource_type.replace('_', ' ').title()
        lines.append('%s' % (resource_title))
        lines.append('~' * len(resource_title))
        lines.append('')

        permission_types = PermissionType.get_valid_permissions_for_resource_type(
            resource_type=resource_type)

        rows = []
        rows.append(TABLE_HEADER)

        for permission_type in permission_types:
            rows.append([permission_type, 'TBD'])
            pass

        table = as_rest_table(rows, full=True)
        lines.extend(table.split('\n'))
        lines.append('')

    result = '\n'.join(lines)
    with open(DESTINATION_PATH, 'w') as fp:
        fp.write(result)

    print('Generated: %s' % (DESTINATION_PATH))
    return result


if __name__ == '__main__':
    main()
