import httplib
import wsmeext.pecan as wsme_pecan
from mongoengine import ValidationError, NotUniqueError
from pecan import abort, expose, request
from pecan.rest import RestController
from st2common import log as logging
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.models.api.reactor import RuleAPI, RuleEnforcementAPI, TriggerAPI
from st2common.models.db.reactor import RuleDB
from st2common.models.base import jsexpose
from st2common.persistence.reactor import Rule, RuleEnforcement, TriggerType, Trigger
from st2common.util import reference
from st2reactorcontroller.service import triggers as TriggerService
from wsme import types as wstypes

LOG = logging.getLogger(__name__)


class RuleController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Rules in the system.
    """
    @jsexpose(str)
    def get_one(self, id):
        """
            List rule by id.

            Handle:
                GET /rules/1
        """
        LOG.info('GET /rules/ with id=%s', id)
        rule_db = RuleController.__get_by_id(id)
        rule_api = RuleAPI.from_model(rule_db)
        LOG.debug('GET /rules/ with id=%s, client_result=%s', id, rule_api)
        return rule_api

    @jsexpose(str)
    def get_all(self, name=None):
        """
            List all rules.

            Handles requests:
                GET /rules/
        """
        LOG.info('GET all /rules/ and name=%s', str(name))
        rule_dbs = Rule.get_all() if name is None else RuleController.__get_by_name(name)
        rule_apis = [RuleAPI.from_model(rule_db) for rule_db in rule_dbs]
        LOG.debug('GET all /rules/ client_result=%s', rule_apis)
        return rule_apis

    @jsexpose(body=RuleAPI, status_code=httplib.CREATED)
    def post(self, rule):
        """
            Create a new rule.

            Handles requests:
                POST /rules/
        """
        LOG.info('POST /rules/ with rule data=%s', rule)

        try:
            rule_db = RuleAPI.to_model(rule)

            trigger_db = TriggerService.create_trigger(TriggerAPI(**rule.trigger))

            rule_db.trigger = reference.get_ref_from_model(trigger_db)
            LOG.debug('/rules/ POST verified RuleAPI and formulated RuleDB=%s', rule_db)
            rule_db = Rule.add_or_update(rule_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for rule data=%s.', rule)
            abort(httplib.BAD_REQUEST, str(e))
            return
        except ValueValidationException as e:
            LOG.exception('Validation failed for rule data=%s.', rule)
            abort(httplib.BAD_REQUEST, str(e))
            return
        except NotUniqueError as e:
            LOG.exception('Rule creation of %s failed with uniqueness conflict.', rule)
            abort(httplib.CONFLICT, str(e))
            return

        LOG.debug('/rules/ POST saved RuleDB object=%s', rule_db)
        rule_api = RuleAPI.from_model(rule_db)
        LOG.debug('POST /rules/ client_result=%s', rule_api)

        return rule_api

    @jsexpose(str, body=RuleAPI, status_code=httplib.OK)
    def put(self, rule_id, rule):
        LOG.info('PUT /rules/ with rule id=%s and data=%s', rule_id, rule)
        rule_db = RuleController.__get_by_id(rule_id)
        LOG.debug('PUT /rules/ lookup with id=%s found object: %s', rule_id, rule_db)

        try:
            if rule.id is not None and rule.id is not '' and rule.id != rule_id:
                LOG.warning('Discarding mismatched id=%s found in payload and using uri_id=%s.',
                            rule.id, rule_id)
            rule_db = RuleAPI.to_model(rule)
            rule_db.id = rule_id

            trigger_db = TriggerService.create_trigger(TriggerAPI(**rule.trigger))
            rule_db.trigger = reference.get_ref_from_model(trigger_db)

            rule_db = Rule.add_or_update(rule_db)
            LOG.debug('/rules/ PUT updated RuleDB object=%s', rule_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for rule data=%s', rule)
            abort(httplib.BAD_REQUEST, str(e))
            return

        rule_api = RuleAPI.from_model(rule_db)
        LOG.debug('PUT /rules/ client_result=%s', rule_api)

        return rule_api

    @jsexpose(str, status_code=httplib.NO_CONTENT)
    def delete(self, rule_id):
        """
            Delete a rule.

            Handles requests:
                DELETE /rules/1
        """
        LOG.info('DELETE /rules/ with id=%s', rule_id)
        rule_db = RuleController.__get_by_id(rule_id)
        LOG.debug('DELETE /rules/ lookup with id=%s found object: %s', rule_id, rule_db)
        try:
            Rule.delete(rule_db)
        except Exception:
            LOG.exception('Database delete encountered exception during delete of id="%s". ', rule_id)

    @staticmethod
    def __get_by_id(rule_id):
        try:
            return Rule.get_by_id(rule_id)
        except (ValueError, ValidationError):
            LOG.exception('Database lookup for id="%s" resulted in exception.', rule_id)
            abort(httplib.NOT_FOUND)

    @staticmethod
    def __get_by_name(rule_name):
        try:
            return [Rule.get_by_name(rule_name)]
        except ValueError as e:
            LOG.debug('Database lookup for name="%s" resulted in exception : %s.', rule_name, e)
            return []


class RuleEnforcementController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of RuleEnforcements in the system.
    """

    @wsme_pecan.wsexpose(RuleEnforcementAPI, wstypes.text)
    def get_one(self, id):
        """
            List ruleenforcement by id.

            Handle:
                GET /ruleenforcements/1
        """
        LOG.info('GET /ruleenforcements/ with id=%s', id)
        try:
            rule_enforcement_db = RuleEnforcement.get_by_id(id)
        except (ValueError, ValidationError):
            LOG.exception('Database lookup for id="%s" resulted in exception.', id)
            abort(httplib.NOT_FOUND)
            return

        rule_enforcement_api = RuleEnforcementAPI.from_model(rule_enforcement_db)
        LOG.debug('GET /ruleenforcements/ with id=%s, client_result=%s', id, rule_enforcement_api)
        return rule_enforcement_api

    @wsme_pecan.wsexpose([RuleEnforcementAPI], wstypes.text)
    def get_all(self):
        """
            List all ruleenforcements.

            Handles requests:
                GET /ruleenforcements/
        """
        LOG.info('GET all /ruleenforcements/')
        rule_enforcement_apis = [RuleEnforcementAPI.from_model(ruleenforcement_db)
                                for ruleenforcement_db in RuleEnforcement.get_all()]
        LOG.debug('GET all /ruleenforcements/ client_result=%s', rule_enforcement_apis)
        return rule_enforcement_apis
