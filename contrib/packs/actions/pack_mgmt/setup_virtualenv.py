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

from st2actions.runners.pythonrunner import Action
from st2common.util.virtualenvs import setup_pack_virtualenv

__all__ = [
    'SetupVirtualEnvironmentAction'
]


class SetupVirtualEnvironmentAction(Action):
    """
    Action which sets up virtual environment for the provided packs.

    Setup consists of the following step:

    1. Create virtual environment for the pack
    2. Install base requirements which are common to all the packs
    3. Install pack-specific requirements (if any)

    If the 'update' parameter is set to True, the setup skips the deletion and
    creation of the virtual environment and performs an update of the
    current dependencies as well as an installation of new dependencies
    """

    def run(self, packs, update=False):
        """
        :param packs: A list of packs to create the environment for.
        :type: packs: ``list``

        :param update: True to update dependencies inside the virtual environment.
        :type update: ``bool``
        """
        for pack_name in packs:
            setup_pack_virtualenv(pack_name=pack_name, update=update, logger=self.logger)

        message = ('Successfuly set up virtualenv for the following packs: %s' %
                   (', '.join(packs)))
        return message
