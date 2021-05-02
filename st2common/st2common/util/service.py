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

from st2common import log as logging


LOG = logging.getLogger(__name__)


def retry_on_exceptions(exc):
    import pymongo

    LOG.warning("Evaluating retry on exception %s. %s", type(exc), str(exc))

    is_mongo_connection_error = isinstance(exc, pymongo.errors.ConnectionFailure)

    retrying = is_mongo_connection_error

    if retrying:
        LOG.warning("Retrying on exception %s.", type(exc))

    return retrying
