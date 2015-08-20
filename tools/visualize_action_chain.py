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
Script which creates graphviz visualization of an action-chain workflow.
"""

import os
import argparse
import sets

try:
    from graphviz import Digraph
except ImportError:
    msg = ('Missing "graphviz" dependency. You can install it using pip: \n'
           'pip install graphviz')
    raise ImportError(msg)

from st2common.content.loader import MetaLoader
from st2actions.runners.actionchainrunner import ChainHolder


def main(metadata_path, output_path, print_source=False):
    metadata_path = os.path.abspath(metadata_path)
    metadata_dir = os.path.dirname(metadata_path)

    meta_loader = MetaLoader()
    data = meta_loader.load(metadata_path)

    action_name = data['name']
    entry_point = data['entry_point']

    workflow_metadata_path = os.path.join(metadata_dir, entry_point)
    chainspec = meta_loader.load(workflow_metadata_path)

    chain_holder = ChainHolder(chainspec, 'workflow')

    graph_label = '%s action-chain workflow visualization' % (action_name)

    graph_attr = {
        'rankdir': 'TD',
        'labelloc': 't',
        'fontsize': '15',
        'label': graph_label
    }
    node_attr = {}
    dot = Digraph(comment='Action chain work-flow visualization',
                  node_attr=node_attr, graph_attr=graph_attr, format='png')
    #  dot.body.extend(['rankdir=TD', 'size="10,5"'])

    # Add all nodes
    node = chain_holder.get_next_node()
    while node:
        dot.node(node.name, node.name)
        node = chain_holder.get_next_node(curr_node_name=node.name)

    # Add connections
    node = chain_holder.get_next_node()
    processed_nodes = sets.Set([node.name])
    nodes = [node]
    while nodes:
        previous_node = nodes.pop()
        success_node = chain_holder.get_next_node(curr_node_name=previous_node.name,
                                                  condition='on-success')
        failure_node = chain_holder.get_next_node(curr_node_name=previous_node.name,
                                                  condition='on-failure')

        # Add success node (if any)
        if success_node:
            dot.edge(previous_node.name, success_node.name, constraint='true',
                     color='green', label='on success')
            if success_node.name not in processed_nodes:
                nodes.append(success_node)
                processed_nodes.add(success_node.name)

        # Add failure node (if any)
        if failure_node:
            dot.edge(previous_node.name, failure_node.name, constraint='true',
                     color='red', label='on failure')
            if failure_node.name not in processed_nodes:
                nodes.append(failure_node)
                processed_nodes.add(failure_node.name)

    if print_source:
        print(dot.source)

    if output_path:
        output_path = os.path.join(output_path, action_name)
    else:
        output_path = output_path or os.path.join(os.getcwd(), action_name)

    dot.format = 'png'
    dot.render(output_path)

    print('Graph saved at %s' % (output_path + '.png'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Action chain visualization')
    parser.add_argument('--metadata-path', action='store', required=True,
                        help='Path to the workflow action metadata file')
    parser.add_argument('--output-path', action='store', required=False,
                        help='Output directory for the generated image')
    parser.add_argument('--print-source', action='store_true', default=False,
                        help='Print graphviz source code to the stdout')
    args = parser.parse_args()

    main(metadata_path=args.metadata_path, output_path=args.output_path,
         print_source=args.print_source)
