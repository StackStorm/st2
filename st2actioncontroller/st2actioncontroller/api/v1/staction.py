from pecan import rest
from st2common.api.controllers.resource import Resource
from st2common import log
from st2common.models.db.staction import Staction as ModelKls
#from stackstorm.storage import staction
from wsme import types as wtypes

import wsmeext.pecan as wsme_pecan

LOG = log.getLogger(__name__)


class Staction(Resource):
    id = wtypes.text
    name = wtypes.text
    repo_path = wtypes.text
    param_names = wtypes.ArrayType(wtypes.text)
    run_type = wtypes.text

    @classmethod
    def from_model(cls, model):
        resource = cls()
        resource.id = str(model.id)
        resource.name = model.name
        resource.repo_path = model.repo_path
        resource.param_names = [param_name for param_name in model.param_names]
        resource.run_type = model.run_type
        return resource


class Stactions(Resource):
    stactions = [Staction]


class StactionController(rest.RestController):

    @wsme_pecan.wsexpose(Staction, wtypes.text)
    def get(self, name):
        model = staction.get_staction_db().get_by_name(name)
        return Staction.from_model(model)

    @wsme_pecan.wsexpose(Stactions, wtypes.text)
    def get_all(self):
        stactions = Stactions()
        stactions.stactions = [Staction.from_model(values) for values in
                               staction.get_staction_db().get_all()]
        return stactions

    @wsme_pecan.wsexpose(Staction, body=Staction, status_code=201)
    def post(self, data):
        LOG.info("Create staction [staction=%s]" % data)
        # TODO(manas) : move to staction runner or inject an intermediate
        # interface rather than direct interaction with db
        model = ModelKls()
        model.name = data.name
        model.repo_path = data.repo_path
        model.param_names = data.param_names
        model.run_type = data.run_type

        model = staction.get_staction_db().add_or_update(model)

        return Staction.from_model(model)
