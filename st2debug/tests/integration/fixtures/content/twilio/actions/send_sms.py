from twilio.rest import TwilioRestClient

from st2actions.runners.pythonrunner import Action


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
