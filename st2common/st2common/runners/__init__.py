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

# Note: Imports are in-line to avoid large import time overhead

from __future__ import absolute_import

from st2common.util import driver_loader

__all__ = ["BACKENDS_NAMESPACE", "get_available_backends", "get_backend_driver"]

BACKENDS_NAMESPACE = "st2common.runners.runner"  # pants: no-infer-dep


def get_available_backends():
    return driver_loader.get_available_backends(namespace=BACKENDS_NAMESPACE)


def get_backend_driver(name):
    return driver_loader.get_backend_driver(namespace=BACKENDS_NAMESPACE, name=name)
