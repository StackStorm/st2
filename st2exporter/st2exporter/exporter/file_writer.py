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

import os

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class FileWriter(object):

    @abc.abstractmethod
    def write(self, data, file_path, replace=False):
        """
        Write data to file_path.
        """
        pass


class TextFileWriter(FileWriter):
    # XXX: Should support compression at some point.

    def write_text(self, text_data, file_path, replace=False, compressed=False):
        if compressed:
            return Exception('Compression not supported.')

        self.write(text_data, file_path, replace=replace)

    def write(self, data, file_path, replace=False):
        if os.path.exists(file_path) and not replace:
            raise Exception('File %s already exists.' % file_path)

        with open(file_path, 'w') as f:
            f.write(data)
            f.flush()
