"""Regression tests for POSIX write completion and timeouts."""

import os
import unittest
from unittest import mock

import serial

try:
    import pty
    import serial.serialposix
except ImportError:
    pty = None


@unittest.skipIf(pty is None, "requires POSIX pseudo terminals")
class TestWriteTimeout(unittest.TestCase):
    def setUp(self):
        self.master, self.slave = pty.openpty()
        self.addCleanup(os.close, self.master)
        self.addCleanup(os.close, self.slave)
        self.serial = serial.Serial(os.ttyname(self.slave), write_timeout=1)
        self.addCleanup(self.serial.close)

    def test_completed_write_does_not_time_out(self):
        data = b'completed before checking the timeout'
        # Simulate descheduling between a successful OS write and the next
        # timeout check. The actual bytes still travel through the PTY.
        with mock.patch('serial.serialutil.time.monotonic', side_effect=[0, 2]):
            self.assertEqual(self.serial.write(data), len(data))
        self.assertEqual(os.read(self.master, len(data)), data)

    def test_partial_write_still_times_out(self):
        data = b'partial write'
        os_write = os.write

        def write_one_byte(fd, chunk):
            return os_write(fd, chunk[:1])

        with mock.patch('serial.serialposix.os.write', side_effect=write_one_byte):
            with mock.patch('serial.serialutil.time.monotonic', side_effect=[0, 2]):
                with self.assertRaises(serial.SerialTimeoutException):
                    self.serial.write(data)
        self.assertEqual(os.read(self.master, 1), data[:1])
