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

import logging
import six
import unittest


class BaseActionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseActionTest, cls).setUpClass()
        cls.log_stream = six.StringIO()
        cls.log_format = '%(asctime)s %(levelname)s [-] %(message)s'
        cls.log_formatter = logging.Formatter(cls.log_format)
        cls.logger = logging.getLogger()
        cls.logger.setLevel(logging.DEBUG)

    @classmethod
    def tearDownClass(cls):
        cls.log_stream.close()
        super(BaseActionTest, cls).tearDownClass()

    def setUp(self):
        super(BaseActionTest, self).setUp()
        self.log_handler = logging.StreamHandler(self.log_stream)
        self.log_handler.setFormatter(self.log_formatter)
        self.log_handler.flush()
        self.logger.addHandler(self.log_handler)

    def tearDown(self):
        self.log_handler.close()
        self.logger.removeHandler(self.log_handler)
        super(BaseActionTest, self).tearDown()
