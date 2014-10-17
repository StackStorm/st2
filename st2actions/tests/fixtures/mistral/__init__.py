import os
import json
import bson
import glob


PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)))
ARTIFACTS = {
    'metadata': {},
    'workflows': {}
}


METADATA_FILES = glob.glob('%s/*.json' % PATH)
for f in METADATA_FILES:
    name = unicode(f.replace(PATH + '/', '').replace('.json', ''))
    with open(f, 'r') as fd:
        ARTIFACTS['metadata'][name] = json.load(fd)
    if isinstance(ARTIFACTS['metadata'][name], dict):
        ARTIFACTS['metadata'][name][u'id'] = unicode(bson.ObjectId())
    elif isinstance(ARTIFACTS['metadata'][name], list):
        for item in ARTIFACTS['metadata'][name]:
            item[u'id'] = unicode(bson.ObjectId())


WORKFLOW_YAMLS = glob.glob('%s/*.yaml' % PATH)
for f in WORKFLOW_YAMLS:
    name = unicode(f.replace(PATH + '/', '').replace('.yaml', ''))
    with open(f, 'r') as fd:
        ARTIFACTS['workflows'][name] = fd.read()
