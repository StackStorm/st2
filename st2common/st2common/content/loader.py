import os


class ContentPackLoader(object):
    def __init__(self):
        self._allowed_content_types = ['sensors', 'actions', 'rules']

    def get_content(self, base_dir=None, content_type=None):
        if content_type is None:
            raise Exception('Content type unknown.')

        if not os.path.isdir(base_dir):
            raise Exception('Directory containing content-packs must be provided.')

        if content_type not in self._allowed_content_types:
            raise Exception('Unknown content type %s.' % content_type)

        content = []
        for pack in os.listdir(base_dir):
            pack_dir = os.path.join(base_dir, pack)
            new_content = None
            try:
                if content_type == 'sensors':
                    new_content = self._get_sensors(pack_dir)
                if content_type == 'actions':
                    new_content = self._get_actions(pack_dir)
                if content_type == 'rules':
                    new_content = self._get_rules(pack_dir)
            except:
                continue
            else:
                content.append(new_content)

        return content

    def _get_sensors(self, pack):
        if 'sensors' not in os.listdir(pack):
            raise Exception('No sensors found.')
        return os.path.join(pack, 'sensors')

    def _get_actions(self, pack):
        if 'actions' not in os.listdir(pack):
            raise Exception('No actions found.')
        return os.path.join(pack, 'actions')

    def _get_rules(self, pack):
        if 'rules' not in os.listdir(pack):
            raise Exception('No rules found.')
        return os.path.join(pack, 'rules')
