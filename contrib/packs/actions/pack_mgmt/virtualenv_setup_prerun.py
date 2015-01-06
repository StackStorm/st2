import six

from st2actions.runners.pythonrunner import Action


class PacksTransformationAction(Action):
    def run(self, packs_status):
        """
        :param packs_status: Result from packs.download action.
        :type: packs_status: ``dict``
        """
        packs = []
        for pack_name, status in six.iteritems(packs_status):
            if 'success' in status.lower():
                packs.append(pack_name)
        return packs
