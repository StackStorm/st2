import wsmeext.pecan as wsme_pecan
from pecan.rest import RestController
from st2common.models.api.reactor import RuleAPI, RuleEnforcementAPI
from st2common.persistence.reactor import Rule, RuleEnforcement
from wsme import types as wstypes


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
        rule_db = Rule.get_by_id(id)
        return RuleAPI.from_model(rule_db)

    @wsme_pecan.wsexpose([RuleAPI], wstypes.text)
    def get_all(self):
        """
            List all rules.

            Handles requests:
                GET /rules/
        """
        return [RuleAPI.from_model(rule_db) for rule_db in Rule.get_all()]

    @wsme_pecan.wsexpose(RuleAPI, body=RuleAPI, status_code=201)
    def post(self, rule):
        """
            Create a new rule.

            Handles requests:
                POST /rules/
        """
        rule_db = RuleAPI.to_model(rule)
        rule_db = Rule.add_or_update(rule_db)
        return RuleAPI.from_model(rule_db)

    @wsme_pecan.wsexpose(None, wstypes.text, status_code=204)
    def delete(self, id):
        """
            Delete a rule.

            Handles requests:
                DELETE /rules/1
        """
        Rule.delete(Rule.get_by_id(id))


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
        ruleenforcement_db = RuleEnforcement.get_by_id(id)
        return RuleEnforcementAPI.from_model(ruleenforcement_db)

    @wsme_pecan.wsexpose([RuleEnforcementAPI], wstypes.text)
    def get_all(self):
        """
            List all ruleenforcements.

            Handles requests:
                GET /ruleenforcements/
        """
        return [RuleEnforcementAPI.from_model(ruleenforcement_db)
                for ruleenforcement_db in RuleEnforcement.get_all()]
