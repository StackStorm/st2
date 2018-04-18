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
from __future__ import absolute_import
import os

import st2common.content.utils as content_utils
from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.api.action import RunnerTypeAPI
from st2common.persistence.runner import RunnerType
from st2common.content.loader import RunnersLoader, MetaLoader
from st2common.constants.runners import MANIFEST_FILE_NAME
from st2common.util.action_db import get_runnertype_by_name
from st2common.util.loader import load_metrics_drivers
import six

__all__ = [
    'register_runner_types',
]


LOG = logging.getLogger(__name__)


def register_metrics(fail_on_failure=True):
    """ Register metrics drivers
    """
    LOG.debug('Start : register metrics')
    driver_count = 0
    # runner_loader = RunnersLoader()

    # if not runner_dirs
        # runner_dirs = ontent_utils.get_runners_base_paths()

    # runners = runner_lader.get_runners(runner_dirs)

    # for runner, path i six.iteritems(runners):
        # LOG.debug('Runer "%s"' % (runner))
        # runner_manifes = os.path.join(path, MANIFEST_FILE_NAME)
        # meta_loader = etaLoader()
        # runner_types =meta_loader.load(runner_manifest)
        # for runner_typ in runner_types:
            # runner_cout += register_runner(runner_type, experimental)
            #
    drivers = load_metrics_drivers()

    for driver in drivers:
        driver_count += 1

    LOG.debug('End : register metrics drivers')

    return driver_count
