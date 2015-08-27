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


"""
"""

import eventlet
import os
import sets
import sys

from oslo_config import cfg

from st2common import config
from st2common.persistence.rule import Rule
from st2common.service_setup import db_setup

try:
    from graphviz import Digraph
except ImportError:
    msg = ('Missing "graphviz" dependency. You can install it using pip: \n'
           'pip install graphviz')
    raise ImportError(msg)


def do_register_cli_opts(opts, ignore_errors=False):
    for opt in opts:
        try:
            cfg.CONF.register_cli_opt(opt)
        except:
            if not ignore_errors:
                raise


def _monkey_patch():
    eventlet.monkey_patch(
        os=True,
        select=True,
        socket=True,
        thread=False if '--use-debugger' in sys.argv else True,
        time=True)


class RuleLink(object):

    def __init__(self, source_action_ref, rule_ref, dest_action_ref):
        self._source_action_ref = source_action_ref
        self._rule_ref = rule_ref
        self._dest_action_ref = dest_action_ref

    def __str__(self):
        return '(%s -> %s -> %s)' % (self._source_action_ref, self._rule_ref, self._dest_action_ref)


class LinksAnalyzer(object):

    def __init__(self):
        self._rule_link_by_action_ref = {}
        self._rules = {}

    def analyze(self, root_action_ref, link_tigger_ref):
        rules = Rule.query(trigger=link_tigger_ref, enabled=True)
        # pprint.pprint([rule.ref for rule in rules])
        for rule in rules:
            source_action_ref = self._get_source_action_ref(rule)
            if not source_action_ref:
                print 'No source_action_ref for rule %s' % rule.ref
                continue
            rule_links = self._rules.get(source_action_ref, None)
            if rule_links is None:
                rule_links = []
                self._rules[source_action_ref] = rule_links
            rule_links.append(RuleLink(source_action_ref=source_action_ref, rule_ref=rule.ref,
                                       dest_action_ref=rule.action.ref))
        analyzed = self._do_analyze(action_ref=root_action_ref)
        for (depth, rule_link) in analyzed:
            print '%s%s' % ('  ' * depth, rule_link)
        return analyzed

    def _get_source_action_ref(self, rule):
        criteria = rule.criteria
        source_action_ref = criteria.get('trigger.action_name', None)
        if not source_action_ref:
            source_action_ref = criteria.get('trigger.action_ref', None)
        return source_action_ref['pattern'] if source_action_ref else None

    def _do_analyze(self, action_ref, rule_links=None, processed=None, depth=0):
        if processed is None:
            processed = sets.Set()
        if rule_links is None:
            rule_links = []
        processed.add(action_ref)
        for rule_link in self._rules.get(action_ref, []):
            rule_links.append((depth, rule_link))
            if rule_link._dest_action_ref in processed:
                continue
            self._do_analyze(rule_link._dest_action_ref, rule_links=rule_links, processed=processed, depth=depth+1)
        return rule_links


class Grapher(object):
    def generate_graph(self, rule_links, out_file):
        graph_label = 'Rule based visualizer'

        graph_attr = {
            'rankdir': 'TD',
            'labelloc': 't',
            'fontsize': '15',
            'label': graph_label
        }
        node_attr = {}
        dot = Digraph(comment='Rule based links visualization',
                      node_attr=node_attr, graph_attr=graph_attr, format='png')

        nodes = sets.Set()
        for _, rule_link in rule_links:
            print rule_link._source_action_ref
            if rule_link._source_action_ref not in nodes:
                nodes.add(rule_link._source_action_ref)
                dot.node(rule_link._source_action_ref, rule_link._source_action_ref)
            if rule_link._dest_action_ref not in nodes:
                nodes.add(rule_link._dest_action_ref)
                dot.node(rule_link._dest_action_ref, rule_link._dest_action_ref)
            dot.edge(rule_link._source_action_ref, rule_link._dest_action_ref, constraint='true', label=rule_link._rule_ref)
        output_path = os.path.join(os.getcwd(), out_file)
        dot.format = 'png'
        dot.render(output_path)


def main():
    _monkey_patch()

    cli_opts = [
        cfg.StrOpt('action_ref', default=None,
                   help='Root action to begin analysis.'),
        cfg.StrOpt('link_trigger_ref', default='core.st2.generic.actiontrigger',
                   help='Root action to begin analysis.'),
        cfg.StrOpt('out_file', default='pipeline')
    ]
    do_register_cli_opts(cli_opts)
    config.parse_args()
    db_setup()
    rule_links = LinksAnalyzer().analyze(cfg.CONF.action_ref, cfg.CONF.link_trigger_ref)
    Grapher().generate_graph(rule_links, cfg.CONF.out_file)


if __name__ == '__main__':
    main()
