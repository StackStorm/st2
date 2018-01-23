from __future__ import absolute_import
import os
import yaml
import glob
import six


PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)))
FILES = glob.glob('%s/*.yaml' % PATH)
ARTIFACTS = {}


for f in FILES:
    f_name = os.path.split(f)[1]
    name = six.text_type(os.path.splitext(f_name)[0])
    with open(f, 'r') as fd:
        ARTIFACTS[name] = yaml.safe_load(fd)
