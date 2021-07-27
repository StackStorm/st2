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
import fnmatch

__all__ = ["StreamingMiddleware"]


class StreamingMiddleware(object):
    def __init__(self, app, path_whitelist=None):
        self.app = app
        self._path_whitelist = path_whitelist or []

    def __call__(self, environ, start_response):
        # Forces eventlet to respond immediately upon receiving a new chunk from endpoint rather
        # than buffering it until the sufficient chunk size is reached. The order for this
        # middleware is not important since it acts as pass-through.

        matches = False
        req_path = environ.get("PATH_INFO", None)

        if not self._path_whitelist:
            matches = True
        else:
            for path_whitelist in self._path_whitelist:
                if fnmatch.fnmatch(req_path, path_whitelist):
                    matches = True
                    break

        if matches:
            environ["eventlet.minimum_write_chunk_size"] = 0

        return self.app(environ, start_response)
