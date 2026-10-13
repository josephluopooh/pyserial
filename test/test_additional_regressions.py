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



def test_closed_loopback_dsr():
    port = serial.serial_for_url('loop://', do_not_open=True)
    with pytest.raises(serial.PortNotOpenError):
        _ = port.dsr
    port.open()
    try:
        port.dtr = False
        assert port.dsr is False
        port.dtr = True
        assert port.dsr is True
    finally:
        port.close()



@pytest.mark.parametrize('space', ['\t', '\n', '\r', '\v', '\f'])
def test_hexlify_incremental_whitespace(space):
    text = '41' + space + '42'
    expected = hexlify_codec.hex_encode(text)[0]
    encoder = hexlify_codec.IncrementalEncoder()
    assert b''.join(encoder.encode(c) for c in text) == expected
    with pytest.raises(UnicodeError):
        encoder.encode('4' + space)



def test_hwgrep_missing_selection_value():
    with pytest.raises(ValueError, match='positive integer'):
        protocol_hwgrep.Serial().from_url('hwgrep://test&n')

