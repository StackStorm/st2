import mock

from st2common.persistence.base import Access
from st2common.persistence.reactor import Rule
from st2tests.base import BaseActionTestCase

from pack_mgmt.unload import UnregisterPackAction


@mock.patch.object(Access, 'delete', mock.MagicMock(return_value=None))
@mock.patch('pack_mgmt.unload.db_setup', mock.MagicMock(return_value=None))
@mock.patch('pack_mgmt.unload.cleanup_trigger_db_for_rule', mock.MagicMock(return_value=None))
class UnregisterPackActionTestCase(BaseActionTestCase):
    action_cls = UnregisterPackAction

    def _get_all_rules(self, pack=None):
        if pack:
            return [x for x in self.mock_rules if x.pack == pack]
        else:
            return self.mock_rules

    def setUp(self):
        super(UnregisterPackActionTestCase, self).setUp()

        self.mock_rules = [self._MockRule('foo', 'bar.trigger', 'baz.action')]

    def test_unregister_rules_of_pack(self):
        action = self.get_action_instance()

        Rule.get_all = mock.MagicMock(side_effect=self._get_all_rules)

        deleted_rules = action._unregister_rules(pack='foo')

        self.assertEqual(len(deleted_rules), 1)

    def test_unregister_rules_of_related_pack(self):
        action = self.get_action_instance()

        Rule.get_all = mock.MagicMock(side_effect=self._get_all_rules)

        deleted_rules = action._unregister_rules(pack='bar')
        self.assertEqual(len(deleted_rules), 1)

        deleted_rules = action._unregister_rules(pack='baz')
        self.assertEqual(len(deleted_rules), 1)

    def test_unregister_rules_of_unrelated_pack(self):
        action = self.get_action_instance()

        Rule.get_all = mock.MagicMock(side_effect=self._get_all_rules)

        deleted_rules = action._unregister_rules(pack='hoge')
        self.assertEqual(deleted_rules, [])

    class _MockRule(object):
        def __init__(self, pack, trigger_ref, action_ref):
            self.pack = pack
            self.trigger = trigger_ref
            self.action = mock.MagicMock()
            self.action.ref = action_ref
