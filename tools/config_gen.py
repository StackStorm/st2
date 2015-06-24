#!/usr/bin/env python
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

import collections
import importlib
import six
import sys
import traceback

from oslo_config import cfg


CONFIGS = ['st2common.config',
           'st2api.config',
           'st2actions.config',
           'st2auth.config',
           'st2reactor.rules.config',
           'st2reactor.sensor.config']

SKIP_GROUPS = ['api_pecan']


def _import_config(config):
    try:
        return importlib.import_module(config)
    except:
        traceback.print_exc()
    return None


def _read_current_config(opt_groups):
    for k, v in six.iteritems(cfg.CONF._groups):
        if k in SKIP_GROUPS:
            continue
        if k not in opt_groups:
            opt_groups[k] = v
    return opt_groups


def _clear_config():
    cfg.CONF.reset()


def _read_group(opt_group):
    for _, opt in six.iteritems(opt_group._opts):
        opt = opt['opt']
        print '# %s' % opt.help
        print '%s = %s' % (opt.name, opt.default)


def _read_groups(opt_groups):
    opt_groups = collections.OrderedDict(sorted(opt_groups.items()))
    for name, opt_group in six.iteritems(opt_groups):
        print '[%s]' % name
        _read_group(opt_group)
        print ''


def main(args):
    opt_groups = {}
    for config in CONFIGS:
        _import_config(config)
        _read_current_config(opt_groups)
        _clear_config()
    _read_groups(opt_groups)


if __name__ == '__main__':
    main(sys.argv)
