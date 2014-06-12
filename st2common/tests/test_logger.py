
import unittest
import os
import uuid
import tempfile

from st2common import log as logging


CONFIG_FILE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                'resources/logging.conf')


class TestLogger(unittest.TestCase):

    def setUp(self):
        super(TestLogger, self).setUp()
        self.config_text = open(CONFIG_FILE_PATH).read()
        self.cfg_fd, self.cfg_path = tempfile.mkstemp()
        self.info_log_fd, self.info_log_path = tempfile.mkstemp()
        self.audit_log_fd, self.audit_log_path = tempfile.mkstemp()
        with open(self.cfg_path, 'a') as f:
            f.write(self.config_text.format(self.info_log_path,
                                            self.audit_log_path))

    def tearDown(self):
        self._remove_tempfile(self.cfg_fd, self.cfg_path)
        self._remove_tempfile(self.info_log_fd, self.info_log_path)
        self._remove_tempfile(self.audit_log_fd, self.audit_log_path)
        super(TestLogger, self).tearDown()

    def _remove_tempfile(self, fd, path):
        os.close(fd)
        os.unlink(path)

    def test_logger_setup_failure(self):
        config_file = '/tmp/abc123'
        self.assertFalse(os.path.exists(config_file))
        self.assertRaises(Exception, logging.setup, config_file)

    def test_log_info(self):
        """Test that INFO log entry does not go to the audit log."""
        logging.setup(self.cfg_path)
        log = logging.getLogger(__name__)
        msg = uuid.uuid4().hex
        log.info(msg)
        info_log_entries = open(self.info_log_path).read()
        self.assertIn(msg, info_log_entries)
        audit_log_entries = open(self.audit_log_path).read()
        self.assertNotIn(msg, audit_log_entries)

    def test_log_critical(self):
        """Test that CRITICAL log entry does not go to the audit log."""
        logging.setup(self.cfg_path)
        log = logging.getLogger(__name__)
        msg = uuid.uuid4().hex
        log.critical(msg)
        info_log_entries = open(self.info_log_path).read()
        self.assertIn(msg, info_log_entries)
        audit_log_entries = open(self.audit_log_path).read()
        self.assertNotIn(msg, audit_log_entries)

    def test_log_audit(self):
        """Test that AUDIT log entry goes to the audit log."""
        logging.setup(self.cfg_path)
        log = logging.getLogger(__name__)
        msg = uuid.uuid4().hex
        log.audit(msg)
        info_log_entries = open(self.info_log_path).read()
        self.assertIn(msg, info_log_entries)
        audit_log_entries = open(self.audit_log_path).read()
        self.assertIn(msg, audit_log_entries)
