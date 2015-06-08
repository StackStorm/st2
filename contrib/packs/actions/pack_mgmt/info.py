from st2actions.runners.pythonrunner import Action
import json
import os

GITINFO_FILE = '.gitinfo'


class PackInfo(Action):
    def run(self, pack, pack_dir="/opt/stackstorm/packs"):
        gitinfo = os.path.join(pack_dir, pack, GITINFO_FILE)
        try:
            with open(gitinfo) as data_file:
                details = json.load(data_file)
                return details
        except:
            print "Unable to load git info for {}".format(pack)
