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
import logging
import logging.config

import six
from jinja2 import Environment, FileSystemLoader

from st2client.commands import Branch
from st2client.commands import Command

__all__ = [
    'PackBranch',
    'PackBootstrapCommand'
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, '../bootstrap_templates')
print TEMPLATES_DIR
LOG = logging.getLogger(__name__)

COMMAND_HELP = {
    'bootstrap': [
        'bootstrap [pack name]',
        'Create initial directory structure for the provided pack.'
    ]
}

DIRECTORY_STRUCTURE = [
    'sensors/',
    'actions/',
]

FILE_TEMPLATES = [
    {
        'name': 'README.md',
        'path': 'README.md'
    },
    {
        'name': 'pack.yaml',
        'path': 'pack.yaml'
    },
    {
        'name': 'config.yaml',
        'path': 'config.yaml'
    }
]


class PackBranch(Branch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(PackBranch, self).__init__(name='pack', description=description, app=app,
                                         subparsers=subparsers, parent_parser=parent_parser)
        self.subparsers = self.parser.add_subparsers(help='Pack management commands')

        self.commands['bootstrap'] = PackBootstrapCommand(name='bootstrap',
                description='bs', app=app, subparsers=self.subparsers,
                parent_parser=parent_parser)


class PackBootstrapCommand(Command):
    def __init__(self, name, description, app, subparsers, parent_parser=None,
            add_help=True):
        super(PackBootstrapCommand, self).__init__(name=name, description=description, app=app,
                                                   subparsers=subparsers,
                                                   parent_parser=parent_parser, add_help=add_help)

        self.parser.add_argument('pack_name',
                                 help='Name of the pack to create.')
        self.parser.add_argument('-i', '--interactive', action='store_true',
                                 help='Run in an interactive mode.')

    def run(self, args, **kwargs):
        self._setup_logging()

        if args.interactive:
            data = self._gather_input(pack_name=args.pack_name)
        else:
            data = {
                'pack_name': args.pack_name,
                'author_name': 'John Doe',
                'author_email': 'john.doe@example.com'
            }

        if not data['pack_name']:
            raise ValueError('Pack name is required')

        self._handle_bootstrap(data=data)

    def run_and_print(self, args, **kwargs):
        self.run(args=args, **kwargs)

    def _gather_input(self, pack_name=None):
        """
        :rtype: ``dict``
        """
        if not pack_name:
            pack_name = six.moves.input('Pack name: ')

        author_name = six.moves.input('Author name: ')
        author_email = six.moves.input('Author email: ')

        data = {
            'pack_name': pack_name,
            'author_name': author_name,
            'author_email': author_email
        }
        return data

    def _get_template_context(self):
        """
        :rtype: ``dict``
        """
        context = {}
        return context

    def _handle_bootstrap(self, data):
        cwd = os.getcwd()
        pack_name = data['pack_name']
        pack_path = os.path.join(cwd, pack_name)

        if os.path.isdir(pack_path):
            raise ValueError('Pack directory "%s" already exists' %
                             (pack_path))

        # 1. Create directory structure
        pack_path = self._create_directory_structure(pack_path=pack_path)

        # 2. Copy over and render the file templates
        context = data
        self._render_and_write_templates(pack_path=pack_path, context=context)

        LOG.info('Pack "%s" created in %s' % (pack_name, pack_path))

    def _create_directory_structure(self, pack_path):
        LOG.debug('Creating directory: %s' % (pack_path))
        os.makedirs(pack_path)

        for directory in DIRECTORY_STRUCTURE:
            full_path = os.path.join(pack_path, directory)
            LOG.debug('Creating directory: %s' % (full_path))
            os.makedirs(full_path)

        return pack_path

    def _render_and_write_templates(self, pack_path, context):
        """
        :param context: Template render context.
        :type context: ``dict``
        """
        env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

        for template_dict in FILE_TEMPLATES:
            template_name = template_dict['name']
            render_path = template_dict['path']

            template = env.get_template(template_name)
            rendered = template.render(**context)

            full_render_path = os.path.join(pack_path, render_path)
            with open(full_render_path, 'w') as fp:
                LOG.debug('Writing template file: %s' % (full_render_path))
                fp.write(rendered)

    def _setup_logging(self):
        logging_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'default': {
                    'format': '%(asctime)s %(levelname)s %(message)s'
                },
            },
            'handlers': {
                'console': {
                    '()': logging.StreamHandler,
                    'formatter': 'default'
                }
            },
            'root': {
                'handlers': ['console'],
                'level': 'INFO',
            },
        }
        logging.config.dictConfig(logging_config)
