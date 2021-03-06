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

from __future__ import absolute_import

import argparse
import string

try:
    from string import letters as ascii_letters
except ImportError:
    from string import ascii_letters

import random


def print_random_chars(chars=1000, selection=ascii_letters + string.digits):
    s = []
    for _ in range(chars - 1):
        s.append(random.choice(selection))
    s.append("@")
    print("".join(s))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chars", type=int, metavar="N", default=10)
    args = parser.parse_args()
    print_random_chars(args.chars)


if __name__ == "__main__":
    main()
