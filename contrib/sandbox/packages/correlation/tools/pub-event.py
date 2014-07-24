#!/usr/bin/python

import sys
import json
import datetime

import requests


st2host = 'localhost'
st2port = '6886'

endpoint = '/webhooks/events'

url = 'http://' + st2host + ':' + st2port + endpoint
headers = {'Content-type': 'application/json'}

host = sys.argv[1]
event_id = sys.argv[2]
timestamp = str(datetime.datetime.utcnow())

payload = {
    'host': host,
    'event_id': str(event_id),
    'timestamp': timestamp
}

data = {
    'name': 'st2.event',
    'event_id': str(event_id),
    'payload': payload
}

r = requests.post(url,data=json.dumps([data]),headers=headers)

print r
