import json
import logging

from st2client import formatters


LOG = logging.getLogger(__name__)


class Json(formatters.Formatter):

    @classmethod
    def format(self, subject, *args, **kwargs):
        attributes = kwargs.get('attributes', None)
        if type(subject) is str:
            subject = json.loads(subject)
        if type(subject) is not list:
            doc = subject if type(subject) is dict else subject.__dict__
            attr = (doc.keys()
                    if not attributes or 'all' in attributes
                    else attributes)
            output = dict((k, v) for k, v in doc.iteritems()
                          if k in attr)
        else:
            output = []
            for item in subject:
                doc = item if type(item) is dict else item.__dict__
                attr = (doc.keys()
                        if not attributes or 'all' in attributes
                        else attributes)
                output.append(dict((k, v) for k, v in doc.iteritems()
                                   if k in attr))
        return json.dumps(output, indent=4)
