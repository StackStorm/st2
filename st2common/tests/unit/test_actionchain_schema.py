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

import unittest2

from jsonschema.exceptions import ValidationError
from st2common.models.system import actionchain
from st2tests.fixturesloader import FixturesLoader

FIXTURES_PACK = 'generic'
TEST_FIXTURES = {
    'actionchains': ['chain1.yaml', 'malformedchain.yaml', 'no_default_chain.yaml',
                     'chain_with_vars.yaml', 'chain_with_publish.yaml']
}
FIXTURES = FixturesLoader().load_fixtures(fixtures_pack=FIXTURES_PACK,
                                          fixtures_dict=TEST_FIXTURES)
CHAIN_1 = FIXTURES['actionchains']['chain1.yaml']
MALFORMED_CHAIN = FIXTURES['actionchains']['malformedchain.yaml']
NO_DEFAULT_CHAIN = FIXTURES['actionchains']['no_default_chain.yaml']
CHAIN_WITH_VARS = FIXTURES['actionchains']['chain_with_vars.yaml']
CHAIN_WITH_PUBLISH = FIXTURES['actionchains']['chain_with_publish.yaml']


class ActionChainSchemaTest(unittest2.TestCase):

    def test_actionchain_schema_valid(self):
        chain = actionchain.ActionChain(**CHAIN_1)
        self.assertEquals(len(chain.chain), len(CHAIN_1['chain']))
        self.assertEquals(chain.default, CHAIN_1['default'])

    def test_actionchain_no_default(self):
        chain = actionchain.ActionChain(**NO_DEFAULT_CHAIN)
        self.assertEquals(len(chain.chain), len(NO_DEFAULT_CHAIN['chain']))
        self.assertEquals(chain.default, None)

    def test_actionchain_with_vars(self):
        chain = actionchain.ActionChain(**CHAIN_WITH_VARS)
        self.assertEquals(len(chain.chain), len(CHAIN_WITH_VARS['chain']))
        self.assertEquals(len(chain.vars), len(CHAIN_WITH_VARS['vars']))

    def test_actionchain_with_publish(self):
        chain = actionchain.ActionChain(**CHAIN_WITH_PUBLISH)
        self.assertEquals(len(chain.chain), len(CHAIN_WITH_PUBLISH['chain']))
        self.assertEquals(len(chain.chain[0].publish),
                          len(CHAIN_WITH_PUBLISH['chain'][0]['publish']))

    def test_actionchain_schema_invalid(self):
        with self.assertRaises(ValidationError):
            actionchain.ActionChain(**MALFORMED_CHAIN)
