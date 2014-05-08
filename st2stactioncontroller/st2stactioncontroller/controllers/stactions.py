from pecan import expose
from pecan.rest import RestController


class StactionsController(RestController):

    @expose('json')
    @expose('text_template.mako', content_type='text/plain')
    def get(self, id):
        return {"dummy": "value"}
