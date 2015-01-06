from st2common.models.db.stormbase import TagField


class TagsHelper(object):

    @staticmethod
    def to_model(tags):
        return [TagField(name=tag.get('name', ''), value=tag.get('value', '')) for tag in tags]

    @staticmethod
    def from_model(tags):
        return [{'name': tag.name, 'value': tag.value} for tag in tags]
