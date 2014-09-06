#!/opt/stackstorm/venvs/correlation/bin/python

"""
This is a sample script to demonstrate use of action to correlate events.
The example here will look at a series of events and if these events are
triggered in a given order within a time window, it'll send a new event
to the event sensor. The script will use the key value store to maintain
state.

Sample correlation rule:
{
    "ordered_events": [ 1008, 1006 ],
    "time_window_in_sec": 5,
    "aggregate_event_id": 3000
}

Setup:
Make sure that a python virtualenv is created under
/opt/stackstorm/repo/venvs/correlation with the appropriate python
modules installed.
"""
from __future__ import print_function

import ast
import sys
import json
import argparse
import datetime

import requests

from st2client.client import Client
from st2client.models.datastore import KeyValuePair
from six.moves import zip

# Parse arguments.
parser = argparse.ArgumentParser(description='Evaluate ordered events.')
parser.add_argument('rule', help='Correlation rule')
parser.add_argument('subject', help='Subject name')
parser.add_argument('event_id', type=int, help='Event ID')
parser.add_argument('timestamp', help='Event timestamp')
args = parser.parse_args()
rule = ast.literal_eval(args.rule)
subject = args.subject
event_id = str(args.event_id)
timestamp = datetime.datetime.strptime(
    args.timestamp, '%Y-%m-%d %H:%M:%S.%f')

# Exit if event id does not match does in aggregation rule.
if event_id not in rule['ordered_events']:
    print('Event is not one of the events being watched.')
    sys.exit()

# Setup client to the key value store
client = Client({
    'api': 'http://localhost:9101'})

# Get existing state data from the key value store
key_name = 'events_ordered_%s' % subject
kvp = client.keys.get_by_name(key_name)

# If kvp does not exist, this means there's no state and
# since this is not the first event in the ordered list,
# we can ignore this event.
if not kvp and rule['ordered_events'][0] != event_id:
    print('Event does not match aggregation criteria.')
    sys.exit()

# Start over if first event in the ordered list.
if rule['ordered_events'][0] == event_id:
    data = {
        'subject': subject,
        'events': [(event_id, str(timestamp))]
    }
    if kvp:
        print('Restarting aggregation state.')
        kvp.value = json.dumps(data)
        client.keys.update(kvp)
    else:
        print('Starting new aggregation state.')
        kvp = KeyValuePair(name=key_name, value=json.dumps(data))
        kvp = client.keys.create(kvp)
    sys.exit()

# Process event
data = json.loads(kvp.value)
events = [event[0] for event in data['events']]
occurred = zip(events, rule['ordered_events'])
num_occurred = len(occurred)

# Determine if the next expected event matches.
if rule['ordered_events'][num_occurred] == event_id:
    # Delete data if time window passes.
    started = datetime.datetime.strptime(
        data['events'][0][1], '%Y-%m-%d %H:%M:%S.%f')
    delta = datetime.timedelta(seconds=rule['time_window_in_sec'])
    ending = started + delta
    if (ending < timestamp):
        print('Event time window passed.')
        print('Event timestamp: %s' % str(timestamp))
        print('Time window ends: %s' % str(ending))
        client.keys.delete(kvp)
        sys.exit()
    else:
        # Fire aggregated event if sequence is completed.
        data['events'].append((event_id, str(timestamp)))
        if len(rule['ordered_events']) == len(data['events']):
            print('Raise aggregated event.')
            url = 'http://localhost:6886/webhooks/events'
            payload = {
                'host': subject,
                'event_id': rule['aggregate_event_id'],
                'timestamp': str(timestamp)
            }
            data = {
                'name': 'st2.event',
                'payload': payload
            }
            headers = {'Content-type': 'application/json'}
            requests.post(url, data=json.dumps([data]), headers=headers)
            client.keys.delete(kvp)
        else:
            # Otherwise, write update.
            print('Update aggregation state.')
            kvp.value = json.dumps(data)
            client.keys.update(kvp)
