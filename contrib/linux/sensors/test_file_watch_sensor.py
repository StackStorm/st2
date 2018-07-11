
import tempfile
import time

import mock
import unittest2

from file_watch_sensor import FileWatchSensor


class TailTestCase(unittest2.TestCase):
    def test_add_trigger_missing_file_path(self):
        sensor_service = mock.MagicMock()
        fws = FileWatchSensor(sensor_service)

        trigger = {
            'parameters': {
                'file_path': None,
            },
        }

        fws_logger = mock.MagicMock()
        fws_tail = mock.MagicMock()

        fws._logger = fws_logger
        fws._tail = fws_tail
        fws.add_trigger(trigger)

        self.assertEqual(fws_logger.error.call_args[0][0],
                         'Received trigger type without "file_path" field.')

    def test_add_trigger_missing_ref(self):
        sensor_service = mock.MagicMock()
        fws = FileWatchSensor(sensor_service)

        trigger = {
            'parameters': {
                'file_path': 'trigger_file_path',
            },
        }

        with self.assertRaises(Exception) as cm:
            fws.add_trigger(trigger)

            self.assertEqual(cm.exception.args[0], 'Trigger %s did not contain a ref.' % trigger)

    def test_remove_trigger_missing_file_path(self):
        sensor_service = mock.MagicMock()
        fws = FileWatchSensor(sensor_service)

        trigger = {
            'parameters': {
                'file_path': 'trigger_file_path',
            },
            'ref': 'ref_file_path',
        }

        fws_logger = mock.MagicMock()
        fws_tail = mock.MagicMock()

        fws._logger = fws_logger
        fws._tail = fws_tail
        fws.add_trigger(trigger)

        self.assertEqual(fws_logger.info.call_args[0][0],
                         'Added file "trigger_file_path"')

        trigger['parameters']['file_path'] = None

        fws.remove_trigger(trigger)

        self.assertEqual(fws_logger.error.call_args[0][0],
                         'Received trigger type without "file_path" field.')

    def test_remove_trigger(self):
        sensor_service = mock.MagicMock()
        fws = FileWatchSensor(sensor_service)

        trigger = {
            'parameters': {
                'file_path': 'trigger_file_path',
            },
            'ref': 'ref_file_path',
        }

        fws_logger = mock.MagicMock()
        fws_tail = mock.MagicMock()

        fws._logger = fws_logger
        fws._tail = fws_tail
        fws.add_trigger(trigger)

        self.assertEqual(fws_logger.info.call_args[0][0],
                         'Added file "trigger_file_path"')

        fws.remove_trigger(trigger)

        self.assertEqual(fws_logger.info.call_args[0][0],
                         'Removed file "trigger_file_path"')

    def test_triggering(self):
        temp_file = tempfile.mktemp()

        sensor_service = mock.MagicMock()
        fws = FileWatchSensor(sensor_service)
        fws.setup()

        trigger = {
            'parameters': {
                'file_path': temp_file,
            },
            'ref': 'ref_file_path',
            'seek_to_end': False,
        }

        with open(temp_file, 'w') as f:
            f.write("Line one\nLine t")

        fws_logger = mock.MagicMock()

        fws._logger = fws_logger
        fws.add_trigger(trigger)
        self.assertEqual(fws_logger.info.call_args[0][0],
                         'Added file "%s"' % temp_file)
        fws.run()
        time.sleep(2)

        with open(temp_file, 'a') as f:
            f.write("wo\nLine three\nLine four")

        time.sleep(2)

        fws.cleanup()
        fws.remove_trigger(trigger)
        self.assertEqual(fws_logger.info.call_args[0][0],
                         'Removed file "%s"' % temp_file)

        self.assertEqual(sensor_service.dispatch.call_count, 4)
        self.assertEqual(sensor_service.dispatch.call_args_list[0][1]['payload']['line'],
                         'Line one')
        self.assertEqual(sensor_service.dispatch.call_args_list[1][1]['payload']['line'],
                         'Line two')
        self.assertEqual(sensor_service.dispatch.call_args_list[2][1]['payload']['line'],
                         'Line three')
        self.assertEqual(sensor_service.dispatch.call_args_list[3][1]['payload']['line'],
                         'Line four')

    def test_triggering_empty_tail_buffer(self):
        temp_file = tempfile.mktemp()

        sensor_service = mock.MagicMock()
        fws = FileWatchSensor(sensor_service)
        fws.setup()

        trigger = {
            'parameters': {
                'file_path': temp_file,
            },
            'ref': 'ref_file_path',
        }

        with open(temp_file, 'w') as f:
            f.write("Line one\nLine t")

        fws_logger = mock.MagicMock()

        fws._logger = fws_logger
        fws.add_trigger(trigger)
        self.assertEqual(fws_logger.info.call_args[0][0],
                         'Added file "%s"' % temp_file)
        fws.run()
        time.sleep(2)

        with open(temp_file, 'a') as f:
            f.write("wo\nLine three\nLine four\n")

        time.sleep(2)

        fws.cleanup()
        fws.remove_trigger(trigger)
        self.assertEqual(fws_logger.info.call_args[0][0],
                         'Removed file "%s"' % temp_file)

        self.assertEqual(sensor_service.dispatch.call_count, 3)
        self.assertEqual(sensor_service.dispatch.call_args_list[0][1]['payload']['line'],
                         'wo')
        self.assertEqual(sensor_service.dispatch.call_args_list[1][1]['payload']['line'],
                         'Line three')
        self.assertEqual(sensor_service.dispatch.call_args_list[2][1]['payload']['line'],
                         'Line four')


if __name__ == '__main__':
    unittest2.main()
