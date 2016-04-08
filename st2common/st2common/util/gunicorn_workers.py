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

import sys

from gunicorn.workers.sync import SyncWorker

__all__ = [
    'EventletSyncWorker'
]


class EventletSyncWorker(SyncWorker):
    """
    Custom sync worker for gunicorn which works with eventlet monkey patching.

    This worker class fixes "AssertionError: do not call blocking functions from
    the mainloop" and some other issues on SIGINT / SIGTERM signal.

    The actual issue happens in "time.sleep" call in "handle_quit" method -
    https://github.com/benoitc/gunicorn/blob/master/gunicorn/workers/base.py#L166
    which results in the assertion failure here -
    https://github.com/simplegeo/eventlet/blob/master/eventlet/greenthread.py#L27
    """

    def handle_quit(self, sig, frame):
        try:
            return super(EventletSyncWorker, self).handle_quit(sig=sig, frame=frame)
        except AssertionError as e:
            msg = str(e)

            if 'do not call blocking functions from the mainloop' in msg:
                # Workaround for "do not call blocking functions from the mainloop" issue
                sys.exit(0)

            raise e
