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

from oslo_config import cfg

from st2common.constants.action import ACTION_OUTPUT_RESULT_DELIMITER

__all__ = [
    'make_read_and_store_stream_func'
]


def make_read_and_store_stream_func(execution_db, action_db, store_line_func):
    """
    Factory function which returns a function for reading from a stream (stdout / stderr).

    This function writes read data into a buffer and stores it in a database.
    """
    def read_and_store_stream(stream, buff):
        try:
            while not stream.closed:
                line = stream.readline()
                if not line:
                    break

                buff.write(line)

                # Filter out result delimiter lines
                if ACTION_OUTPUT_RESULT_DELIMITER in line:
                    continue

                if cfg.CONF.actionrunner.store_output:
                    store_line_func(execution_db=execution_db, action_db=action_db, line=line)
        except RuntimeError:
            # process was terminated abruptly
            pass

    return read_and_store_stream
