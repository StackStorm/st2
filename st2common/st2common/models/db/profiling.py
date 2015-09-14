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
Module containing MongoDB profiling related functionality.
"""

from st2common import log as logging

__all__ = [
    'log_query_and_profile_data_for_queryset'
]

LOG = logging.getLogger(__name__)

ENABLE_PROFILING = False


def log_query_and_profile_data_for_queryset(queryset):
    """
    Function which logs MongoDB query and profile data for the provided mongoengine queryset object.

    Keep in mind that this method needs to be called at the very end after all the mongoengine
    methods are chained.

    For example:

    result = model.object(...)
    result = model.limit(...)
    result = model.order_by(...)
    """
    if not ENABLE_PROFILING:
        # Profiling is disabled
        return queryset

    query = getattr(queryset, '_query', None)
    mongo_query = getattr(queryset, '_mongo_query', query)
    ordering = getattr(queryset, '_ordering', None)
    limit = getattr(queryset, '_limit', None)
    collection = getattr(queryset, '_collection', None)
    collection_name = getattr(collection, 'name', None)

    # Note: We need to clone the queryset when using explain because explain advances the cursor
    # internally which changes the function result
    cloned_queryset = queryset.clone()
    explain_info = cloned_queryset.explain(format=True)

    if mongo_query is not None and collection_name is not None:
        mongo_shell_query = construct_mongo_shell_query(mongo_query=mongo_query,
                                                        collection_name=collection_name,
                                                        ordering=ordering,
                                                        limit=limit)
        extra = {'mongo_query': mongo_query, 'mongo_shell_query': mongo_shell_query}
        LOG.debug('MongoDB query: %s' % (mongo_shell_query), extra=extra)
        LOG.debug('MongoDB explain data: %s' % (explain_info))

    return queryset


def construct_mongo_shell_query(mongo_query, collection_name, ordering, limit):
    result = []

    # Select collection
    part = 'db.{collection}'.format(collection=collection_name)
    result.append(part)

    # Include filters (if any)
    if mongo_query:
        filter_predicate = mongo_query
    else:
        filter_predicate = ''

    part = 'find({filter_predicate})'.format(filter_predicate=filter_predicate)
    result.append(part)

    # Include ordering info (if any)
    if ordering:
        sort_predicate = []
        for field_name, direction in ordering:
            sort_predicate.append('{name}: {direction}'.format(name=field_name,
                                                              direction=direction))

        sort_predicate = ', '.join(sort_predicate)
        part = 'sort({{{sort_predicate}}})'.format(sort_predicate=sort_predicate)
        result.append(part)

    # Include limit info (if any)
    if limit is not None:
        part = 'limit({limit})'.format(limit=limit)
        result.append(part)

    result = '.'.join(result) + ';'
    return result
