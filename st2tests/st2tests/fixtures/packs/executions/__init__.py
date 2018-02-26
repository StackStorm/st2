from __future__ import absolute_import
import os
import bson
import glob
import yaml
import six


PATH = os.path.dirname(os.path.realpath(__file__))
FILES = glob.glob('%s/*.yaml' % PATH)
ARTIFACTS = {}


for f in FILES:
    f_name = os.path.split(f)[1]
    name = six.text_type(os.path.splitext(f_name)[0])
    with open(f, 'r') as fd:
        ARTIFACTS[name] = yaml.safe_load(fd)
    if isinstance(ARTIFACTS[name], dict):
        ARTIFACTS[name][u'id'] = six.text_type(bson.ObjectId())
    elif isinstance(ARTIFACTS[name], list):
        for item in ARTIFACTS[name]:
            item[u'id'] = six.text_type(bson.ObjectId())
