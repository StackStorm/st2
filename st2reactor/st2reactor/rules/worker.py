from st2common.transport.reactor import get_trigger_queue


def work():
    # TODO Listen on this queue and dispatch message to the rules engine
    queue = get_trigger_queue(name='st2.trigger_dispatch.rules_engine',
                              routing_key='#')
    pass
