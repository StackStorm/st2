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

import logging

__all__ = [
    'reopen_log_files'
]

LOG = logging.getLogger(__name__)


def reopen_log_files(handlers):
    """
    This method iterates through all of the providers handlers looking for the FileHandler types.

    A lock is acquired, the underlying stream closed, reopened, then the lock is released.


    This method should be called when logs are to be rotated by an external process. The simplest
    way to do this is via a signal handler.
    """
    for handler in handlers:
        if not isinstance(handler, logging.FileHandler):
            continue

        LOG.info('Re-opening log file "%s" with mode "%s"\n' %
                 (handler.baseFilename, handler.mode))
        try:
            handler.acquire()
            handler.stream.close()
            handler.stream = open(handler.baseFilename, handler.mode)
        finally:
            handler.release()
