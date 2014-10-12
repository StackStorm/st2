#!/usr/bin/env python

import argparse
try:
    import simplejson as json
except ImportError:
    import json
import os
import sys

from twilio.rest import TwilioRestClient


def _get_twilio_client(twilio_creds):
    return TwilioRestClient(twilio_creds['account_sid'], twilio_creds['auth_token'])


def _send_sms(client=None, body=None, from_=None, to=None):
    client.messages.create(body=body, from_=from_, to=to)


def main(args):
    config_file_path = os.path.join(os.path.dirname(__file__), 'lib/config.json')

    twilio_creds = {}
    if os.path.exists(config_file_path):
        with open(config_file_path) as json_file:
            twilio_creds = json.load(json_file)

    if args['account_sid']:
        twilio_creds['account_sid'] = args['account_sid']
    if args['auth_token']:
        twilio_creds['auth_token'] = args['auth_token']

    twilio_client = _get_twilio_client(twilio_creds)
    try:
        _send_sms(client=twilio_client, body=args['body'], from_=args['from'], to=args['to'])
        sys.stdout.write('Successfully sent sms to: %s\n' % args['to'])
    except Exception as e:
        sys.stderr.write('Failed sending sms to: %s, exception: %s\n' % (args['to'], str(e)))
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Twilio sms action')
    parser.add_argument('-body', '--body', help='Body of the message.', required=True)
    parser.add_argument('-to', '--to', help='Recipient number. E.164 format.', required=True)
    parser.add_argument('-from', '--from', help='Twilio "from" number. E.164 format.',
                        required=True)
    parser.add_argument('-id', '--account-sid', help='Twilio account sid.', required=True)
    parser.add_argument('-token', '--auth-token', help='Twilio account sid.', required=True)
    args = vars(parser.parse_args())
    main(args)
