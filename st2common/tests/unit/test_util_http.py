#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest2

from st2common.util.http import parse_content_type_header

__all__ = [
    'HTTPUtilTestCase'
]


class HTTPUtilTestCase(unittest2.TestCase):
    def test_parse_content_type_header(self):
        values = [
            'application/json',
            'foo/bar',
            'application/json; charset=utf-8',
            'application/json; charset=utf-8; foo=bar',
        ]
        expected_results = [
            ('application/json', {}),
            ('foo/bar', {}),
            ('application/json', {'charset': 'utf-8'}),
            ('application/json', {'charset': 'utf-8', 'foo': 'bar'})
        ]

        for value, expected_result in zip(values, expected_results):
            result = parse_content_type_header(content_type=value)
            self.assertEqual(result, expected_result)
