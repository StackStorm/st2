import glob
import json

from oslo.config import cfg

from st2api.service import triggers as TriggerService
from st2common import log as logging
from st2common.models.api.reactor import RuleAPI, TriggerAPI
from st2common.persistence.reactor import Rule
from st2common.util import reference

LOG = logging.getLogger(__name__)


def register_rules():
    rules = glob.glob(cfg.CONF.rules.rules_path + '/*.json')
    for rule in rules:
        LOG.debug('Loading rule from %s.', rule)
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
