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

from st2tests.fixturesloader import FixturesLoader
from tests import FunctionalTest

__all__ = [
    'JsexposeDecoratorTestCase'
]

FIXTURES_PACK = 'aliases'

TEST_MODELS = {
    'aliases': ['alias1.yaml', 'alias2.yaml']
}


class JsexposeDecoratorTestCase(FunctionalTest):
    """
    Test case which tests various invalid requests and makes sure they are correctly handled by
    the jsexpose decorator.
    """

    models = None
    alias1 = None

    @classmethod
    def setUpClass(cls):
        super(JsexposeDecoratorTestCase, cls).setUpClass()
        cls.models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                          fixtures_dict=TEST_MODELS)
        cls.alias1 = cls.models['aliases']['alias1.yaml']

    def test_invalid_number_of_arguments_results_in_resource_not_found(self):
        # Invalid path (additional path components after the id)
        resp = self.app.get('/v1/actionalias/%s/some/more/args' % (self.alias1.id),
                            expect_errors=True)
        self.assertEqual(resp.status_int, 404)
        self.assertEqual(resp.json['faultstring'], 'The resource could not be found.')

    def test_invalid_query_param_results_in_bad_request(self):
        resp = self.app.get('/v1/actionalias/%s?invalid=arg' % (self.alias1.id), expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertEqual(resp.json['faultstring'], 'Unsupported query parameter: invalid')
