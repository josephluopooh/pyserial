"""The loop transport must apply timeouts to the whole operation."""

import queue
from unittest import mock

import serial
import pytest
from serial.urlhandler import protocol_loop


def test_read_uses_remaining_timeout():
    now = [0.0]
    with serial.serial_for_url('loop://', timeout=1) as port:
        calls = []

        def receive(timeout):
            calls.append(timeout)
            if len(calls) == 1:
                now[0] = 0.75
                return b'a'
            assert timeout == 0.25
            now[0] = 1.0
            raise queue.Empty

        with mock.patch.object(port.queue, 'get', side_effect=receive), \
                mock.patch('serial.serialutil.time.monotonic', side_effect=lambda: now[0]):
            assert port.read(2) == b'a'
        assert calls == [1.0, 0.25]


def test_full_loop_buffer_raises_serial_timeout():
    port = protocol_loop.Serial(None, baudrate=115200, write_timeout=0.01)
    port.port = 'loop://'
    port.buffer_size = 1
    with port:
        with pytest.raises(serial.SerialTimeoutException):
            port.write(b'ab')
