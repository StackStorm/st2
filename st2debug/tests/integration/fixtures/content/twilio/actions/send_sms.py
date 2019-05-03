# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from twilio.rest import TwilioRestClient

from st2common.runners.base_action import Action


class TwilioSendSMSAction(Action):
    def __init__(self, config):
        super(TwilioSendSMSAction, self).__init__(config=config)
        self.client = TwilioRestClient(self.config['account_sid'],
                                       self.config['auth_token'])

    def run(self, from_number, to_number, body):
        try:
            self.client.messages.create(body=body, from_=from_number, to=to_number)
        except Exception as e:
            error_msg = ('Failed sending sms to: %s, exception: %s\n' %
                         (to_number, str(e.msg)))
            self.logger.error(error_msg)
            raise Exception(error_msg)

        self.logger.info('Successfully sent sms to: %s\n' % (to_number))
