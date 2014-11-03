import os
import json
import bson
import glob


PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)))
FILES = glob.glob('%s/*.json' % PATH)
ARTIFACTS = {}


for f in FILES:
    name = unicode(f.replace(PATH + '/', '').replace('.json', ''))
    with open(f, 'r') as fd:
        ARTIFACTS[name] = json.load(fd)
    if isinstance(ARTIFACTS[name], dict):
        ARTIFACTS[name][u'id'] = unicode(bson.ObjectId())
    elif isinstance(ARTIFACTS[name], list):
        for item in ARTIFACTS[name]:
            item[u'id'] = unicode(bson.ObjectId())
