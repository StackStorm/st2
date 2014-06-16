import httplib
import wsmeext.pecan as wsme_pecan
from mongoengine import ValidationError
from pecan import abort
from pecan.rest import RestController
from st2common import log as logging
from st2common.models.api.reactor import RuleAPI, RuleEnforcementAPI
from st2common.persistence.reactor import Rule, RuleEnforcement
from wsme import types as wstypes

LOG = logging.getLogger(__name__)


class RuleController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Rules in the system.
    """
    @wsme_pecan.wsexpose(RuleAPI, wstypes.text)
    def get_one(self, id):
        """
            List rule by id.

            Handle:
                GET /rules/1
        """
        LOG.info('GET /rules/ with id=%s', id)
        rule_db = RuleController._get_by_id(id)
        rule_api = RuleAPI.from_model(rule_db)
        LOG.debug('GET /rules/ with id=%s, client_result=%s', id, rule_api)
        return rule_api

    @wsme_pecan.wsexpose([RuleAPI], wstypes.text)
    def get_all(self):
        """
            List all rules.

            Handles requests:
                GET /rules/
        """
        LOG.info('GET all /rules/')
        rule_apis = [RuleAPI.from_model(rule_db) for rule_db in Rule.get_all()]
        LOG.debug('GET all /rules/ client_result=%s', rule_apis)
        return rule_apis

    @wsme_pecan.wsexpose(RuleAPI, body=RuleAPI, status_code=201)
    def post(self, rule):
        """
            Create a new rule.

            Handles requests:
                POST /rules/
        """
        LOG.info('POST /rules/ with rule data=%s', rule)

        try:
            rule_db = RuleAPI.to_model(rule)
            LOG.debug('/rules/ POST verified RuleAPI and formulated RuleDB=%s', rule_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for rule data=%s.', rule)
            abort(httplib.BAD_REQUEST, str(e))

        rule_db = Rule.add_or_update(rule_db)
        LOG.debug('/rules/ POST saved RuleDB object=%s', rule_db)

        rule_api = RuleAPI.from_model(rule_db)
        LOG.debug('POST /rules/ client_result=%s', rule_api)

        return rule_api

    @wsme_pecan.wsexpose(None, wstypes.text, status_code=httplib.NO_CONTENT)
    def delete(self, id):
        """
            Delete a rule.

            Handles requests:
                DELETE /rules/1
        """
        LOG.info('DELETE /rules/ with id=%s', id)
        rule_db = RuleController._get_by_id(id)
        LOG.debug('DELETE /rules/ lookup with id=%s found object: %s', id, rule_db)
        try:
            Rule.delete(rule_db)
        except Exception:
            LOG.exception('Database delete encountered exception during delete of id="%s". ', id)

    @staticmethod
    def _get_by_id(rule_id):
        try:
            return Rule.get_by_id(rule_id)
        except (ValueError, ValidationError):
            LOG.exception('Database lookup for id="%s" resulted in exception.', rule_id)
            abort(httplib.NOT_FOUND)


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
