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
Module with utility functions for purging old trigger instance objects.
"""

from mongoengine.errors import InvalidQueryError

from st2common.persistence.trigger import TriggerInstance
from st2common.util import isotime

__all__ = [
    'purge_trigger_instances'
]


def purge_trigger_instances(logger, timestamp):
    """
    :param timestamp: Trigger instances older than this timestamp will be deleted.
    :type timestamp: ``datetime.datetime
    """
    if not timestamp:
        raise ValueError('Specify a valid timestamp to purge.')

    logger.info('Purging trigger instances older than timestamp: %s' %
                timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))

    query_filters = {'occurrence_time__lt': isotime.parse(timestamp)}

    # TODO: Update this code to return statistics on deleted objects once we
    # upgrade to newer version of MongoDB where delete_by_query actually returns
    # some data

    try:
        TriggerInstance.delete_by_query(**query_filters)
    except InvalidQueryError as e:
        msg = ('Bad query (%s) used to delete trigger instances: %s'
               'Please contact support.' % (query_filters, str(e)))
        raise InvalidQueryError(msg)
    except:
        logger.exception('Deleting instances using query_filters %s failed.', query_filters)

    # Print stats
    logger.info('All trigger instance models older than timestamp %s were deleted.', timestamp)
