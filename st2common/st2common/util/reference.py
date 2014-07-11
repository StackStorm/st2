from st2common.exceptions import db


def get_ref_from_model(model):
    if model is None:
        raise ValueError('Model should has None value.')
    model_id = getattr(model, 'id', None)
    if model_id is None:
        raise db.StackStormDBObjectMalformedError('model %s must contain id.' % str(model))
    reference = {'id': str(model_id),
                 'name': getattr(model, 'name', None)}
    return reference


def get_model_from_ref(db_api, reference):
    if reference is None:
        raise db.StackStormDBObjectNotFoundError('No reference supplied.')
    model_id = reference.get('id', None)
    if model_id is not None:
        return db_api.get_by_id(model_id)    
    model_name = reference.get('name', None)
    if model_name is None:
        raise db.StackStormDBObjectNotFoundError('Both name and id are None.')
    return db_api.get_by_name(model_name)
