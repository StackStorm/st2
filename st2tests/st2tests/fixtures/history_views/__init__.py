import os
import json
import glob


PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)))
FILES = glob.glob('%s/*.json' % PATH)
ARTIFACTS = {}


for f in FILES:
    name = unicode(f.replace(PATH + '/', '').replace('.json', ''))
    with open(f, 'r') as fd:
        ARTIFACTS[name] = json.load(fd)
