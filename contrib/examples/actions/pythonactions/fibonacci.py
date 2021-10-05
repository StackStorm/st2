#!/usr/bin/env python
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

from __future__ import print_function
import sys
import traceback

import six
from six.moves import map


def fib(n):
    if n < 2:
        return n
    return fib(n - 2) + fib(n - 1)


if __name__ == "__main__":
    try:
        startNumber = int(float(sys.argv[1]))
        endNumber = int(float(sys.argv[2]))
        results = map(str, map(fib, list(range(startNumber, endNumber))))
        results = " ".join(results)
        print(results)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        sys.exit(six.text_type(e))
