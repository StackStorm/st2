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

import json
import logging

from st2client import formatters
import six


LOG = logging.getLogger(__name__)


class Json(formatters.Formatter):

    @classmethod
    def format(self, subject, *args, **kwargs):
        attributes = kwargs.get('attributes', None)
        if type(subject) is str:
            subject = json.loads(subject)
        if type(subject) is not list:
            doc = subject if type(subject) is dict else subject.__dict__
            attr = (doc.keys()
                    if not attributes or 'all' in attributes
                    else attributes)
            output = dict((k, v) for k, v in six.iteritems(doc)
                          if k in attr)
        else:
            output = []
            for item in subject:
                doc = item if type(item) is dict else item.__dict__
                attr = (doc.keys()
                        if not attributes or 'all' in attributes
                        else attributes)
                output.append(dict((k, v) for k, v in six.iteritems(doc)
                                   if k in attr))
        return json.dumps(output, indent=4)
