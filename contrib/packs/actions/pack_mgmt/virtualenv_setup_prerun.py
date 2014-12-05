import six

from st2actions.runners.pythonrunner import Action


class PacksTransformationAction(Action):
    def run(self, packs_status):
        """
        :param packs: A list of packs to create the environment for.
        :type: packs: ``list``
        """
        packs = []
        for pack_name, status in six.iteritems(packs_status):
            packs.append(pack_name)
        return packs
