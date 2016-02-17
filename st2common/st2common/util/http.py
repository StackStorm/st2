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

import six

http_client = six.moves.http_client

__all__ = [
    'HTTP_SUCCESS',
    'parse_content_type_header'
]

HTTP_SUCCESS = [http_client.OK, http_client.CREATED, http_client.ACCEPTED,
                http_client.NON_AUTHORITATIVE_INFORMATION, http_client.NO_CONTENT,
                http_client.RESET_CONTENT, http_client.PARTIAL_CONTENT,
                http_client.MULTI_STATUS, http_client.IM_USED,
                ]


def parse_content_type_header(content_type):
    """
    Parse and normalize request content type and return a tuple with the content type and the
    options.

    :rype: ``tuple``
    """
    if ';' in content_type:
        split = content_type.split(';')
        media = split[0]
        options = {}

        for pair in split[1:]:
            split_pair = pair.split('=', 1)

            if len(split_pair) != 2:
                continue

            key = split_pair[0].strip()
            value = split_pair[1].strip()

            options[key] = value
    else:
        media = content_type
        options = {}

    result = (media, options)
    return result
