# Copyright 2022 The StackStorm Authors.
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
Module with utility functions for purging old trigger instance objects.
"""

from __future__ import absolute_import

import six
from mongoengine.errors import InvalidQueryError

from st2common.persistence.auth import Token
from st2common.util import isotime

__all__ = ["purge_tokens"]


def purge_tokens(logger, timestamp):
    """
    :param timestamp: Tokens which expired after this timestamp will be deleted.
    :type timestamp: ``datetime.datetime
    """
    if not timestamp:
        raise ValueError("Specify a valid timestamp to purge.")

    logger.info(
        "Purging token instances which expired after timestamp: %s"
        % timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    )

    query_filters = {"expiry__lt": isotime.parse(timestamp)}

    try:
        deleted_count = Token.delete_by_query(**query_filters)
    except InvalidQueryError as e:
        msg = (
            "Bad query (%s) used to delete token instances: %s"
            "Please contact support."
            % (
                query_filters,
                six.text_type(e),
            )
        )
        raise InvalidQueryError(msg)
    except:
        logger.exception(
            "Deleting token instances using query_filters %s failed.", query_filters
        )
    else:
        logger.info("Deleted %s token objects" % (deleted_count))

    # Print stats
    logger.info("All token models expired after timestamp %s were deleted.", timestamp)
