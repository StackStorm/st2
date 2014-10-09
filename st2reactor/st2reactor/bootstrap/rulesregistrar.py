import glob
import json

from oslo.config import cfg
import six

from st2common import log as logging
from st2common.content.loader import ContentPackLoader
from st2common.models.api.reactor import RuleAPI, TriggerAPI
from st2common.persistence.reactor import Rule
from st2common.services import triggers as TriggerService
from st2common.util import reference

LOG = logging.getLogger(__name__)


def _get_rules_from_pack(pack):
    return glob.glob(pack + '/*.json')


def _register_rules_from_pack(pack, rules):
    for rule in rules:
        LOG.debug('Loading rule from %s.', rule)
        try:
            with open(rule, 'r') as fd:
                try:
                    content = json.load(fd)
                except ValueError:
                    LOG.exception('Unable to load rule from %s.', rule)
                    continue
                rule_api = RuleAPI(**content)
                trigger_api = TriggerAPI(**rule_api.trigger)

                rule_db = RuleAPI.to_model(rule_api)
                trigger_db = TriggerService.create_trigger_db(trigger_api)

                try:
                    rule_db.id = Rule.get_by_name(rule_api.name).id
                except ValueError:
                    LOG.info('Rule %s not found. Creating new one.', rule)

                rule_db.trigger = reference.get_ref_from_model(trigger_db)

                try:
                    rule_db = Rule.add_or_update(rule_db)
                    LOG.audit('Rule updated. Rule %s from %s.', rule_db, rule)
                except Exception:
                    LOG.exception('Failed to create rule %s.', rule_api.name)
        except:
            LOG.exception('Failed registering rule from %s.', rule)


def _register_rules_from_packs(base_dir):
    pack_loader = ContentPackLoader()
    dirs = pack_loader.get_content(base_dir=base_dir,
                                   content_type='rules')
    for pack, rules_dir in six.iteritems(dirs):
        try:
            LOG.info('Registering rules from pack: %s', pack)
            rules = _get_rules_from_pack(rules_dir)
            _register_rules_from_pack(pack, rules)
        except:
            LOG.exception('Failed registering all rules from pack: %s', rules_dir)


def register_rules(content_packs_base_path=None):
    if not content_packs_base_path:
        content_packs_base_path = cfg.CONF.content.content_packs_base_path
    return _register_rules_from_packs(content_packs_base_path)
