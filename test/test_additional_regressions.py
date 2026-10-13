"""Regression tests for serial error handling and URL parsing."""
from unittest import mock
import pytest
import serial
import serial.rs485
from serial.tools import hexlify_codec
from serial.urlhandler import protocol_hwgrep


@pytest.mark.parametrize('failure', ['write', 'flush'])
def test_rs485_restores_rts_on_error(failure):
    port = serial.rs485.RS485()
    port.rs485_mode = serial.rs485.RS485Settings()
    with mock.patch.object(serial.Serial, 'write'), mock.patch.object(serial.Serial, 'flush'), \
            mock.patch.object(serial.Serial, failure, side_effect=serial.SerialException('failed')):
        with pytest.raises(serial.SerialException, match='failed'):
            port.write(b'data')
    assert port.rts is False

