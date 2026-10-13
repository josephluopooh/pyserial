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



@pytest.mark.parametrize('typecode', ['B', 'b', 'H', 'I'])
def test_readinto_typed_arrays(typecode):
    import array
    target = array.array(typecode, [0, 0])
    view = memoryview(target).cast('B')
    data = bytes(range(1, view.nbytes + 1))
    with serial.serial_for_url('loop://', timeout=0) as port:
        port.write(data)
        assert port.readinto(target) == len(data)
    assert bytes(view) == data


def test_readinto_rejects_readonly_before_consuming_data():
    with serial.serial_for_url('loop://', timeout=0) as port:
        port.write(b'abc')
        with pytest.raises(TypeError):
            port.readinto(b'...')
        assert port.read(3) == b'abc'



def test_send_break_restores_idle_after_interruption():
    with serial.serial_for_url('loop://') as port:
        with mock.patch('serial.serialutil.time.sleep', side_effect=KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                port.send_break()
        assert port.break_condition is False



def test_timeout_restart_zero_updates_flags():
    from serial.serialutil import Timeout
    timeout = Timeout(1)
    timeout.restart(0)
    assert timeout.is_non_blocking
    assert timeout.expired()
    timeout.restart(1)
    assert not timeout.is_non_blocking
    assert not timeout.is_infinite



@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1, 1j])
def test_rfc2217_read_timeout_validation(value):
    from serial.rfc2217 import Serial
    port = Serial()
    with pytest.raises(ValueError):
        port.timeout = value


@pytest.mark.parametrize('value', ['nan', 'inf', '-1', '0'])
def test_rfc2217_network_timeout_validation(value):
    from serial.rfc2217 import Serial
    with pytest.raises(serial.SerialException):
        Serial().from_url('rfc2217://localhost:1234?timeout=' + value)

