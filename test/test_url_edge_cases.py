"""Regression tests for URL handler boundary cases."""

from unittest import mock

import pytest
import serial
from serial.urlhandler import protocol_alt, protocol_hwgrep, protocol_spy
from serial.tools import hexlify_codec


def test_hwgrep_first_port():
    with mock.patch('serial.tools.list_ports.grep', return_value=[('/dev/test', '', '')]):
        assert protocol_hwgrep.Serial().from_url('hwgrep://test&n=1') == '/dev/test'
    for value in ('0', '-1'):
        with pytest.raises(ValueError):
            protocol_hwgrep.Serial().from_url('hwgrep://test&n=' + value)



def test_hwgrep_uppercase_scheme():
    with mock.patch('serial.tools.list_ports.grep', return_value=[('/dev/test', '', '')]):
        port = serial.serial_for_url('HWGREP://test', do_not_open=True)
        assert port.port == '/dev/test'



def test_alt_non_class():
    with pytest.raises(ValueError, match='not an instance of Serial'):
        protocol_alt.serial_class_for_url('alt:///dev/test?class=VERSION')



def test_hexlify_empty_decoder_chunks():
    assert hexlify_codec.hex_decode(b'') == ('', 0)
    assert hexlify_codec.Codec().decode(b'') == ('', 0)
    decoder = hexlify_codec.IncrementalDecoder()
    assert decoder.decode(b'') == ''
    assert decoder.decode(b'A') == '41 '
    assert decoder.decode(b'', final=True) == ''



def test_hexlify_incomplete_final_pair():
    encoder = hexlify_codec.IncrementalEncoder()
    assert encoder.encode('4') == b''
    with pytest.raises(UnicodeError, match='odd number'):
        encoder.encode('', final=True)
    encoder.reset()
    assert encoder.encode('41', final=True) == b'A'
    ignoring = hexlify_codec.IncrementalEncoder(errors='ignore')
    assert ignoring.encode('4', final=True) == b''
    assert ignoring.getstate() == 0



def test_spy_direct_initialization():
    with mock.patch.object(serial.Serial, 'open'):
        port = protocol_spy.Serial('spy:///dev/test?all')
    assert isinstance(port.formatter, protocol_spy.FormatHexdump)
    assert port.show_all is True



def test_spy_clear_port():
    port = serial.serial_for_url('spy:///dev/test', do_not_open=True)
    port.port = None
    assert port.port is None
    assert port.name is None



@pytest.mark.parametrize('setting', ['timeout', 'write_timeout', 'inter_byte_timeout'])
@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf'), 'bad', complex(1, 1)])
def test_invalid_timeout_values(setting, value):
    port = serial.Serial()
    with pytest.raises(ValueError):
        setattr(port, setting, value)



def test_packetizer_reconnect_discards_partial_packet():
    from serial.threaded import Packetizer
    protocol = Packetizer()
    protocol.handle_packet = mock.Mock()
    protocol.connection_made(mock.Mock())
    protocol.data_received(b'old')
    protocol.connection_lost(None)
    protocol.connection_made(mock.Mock())
    protocol.data_received(b'new\x00')
    protocol.handle_packet.assert_called_once_with(bytearray(b'new'))



def test_frame_stop_outside_packet():
    from serial.threaded import FramedPacket
    protocol = FramedPacket()
    protocol.handle_packet = mock.Mock()
    protocol.handle_out_of_packet_data = mock.Mock()
    protocol.data_received(b')(ok))')
    protocol.handle_packet.assert_called_once_with(b'ok')
    assert protocol.handle_out_of_packet_data.call_args_list == [mock.call(b')'), mock.call(b')')]



@pytest.mark.parametrize('factory_error', [False, True])
def test_reader_initialization_error_signals_waiters(factory_error):
    from serial.threaded import ReaderThread
    protocol = mock.Mock()
    protocol.connection_made.side_effect = ValueError('initialize')
    protocol.connection_lost.side_effect = ValueError('cleanup')
    factory = mock.Mock(side_effect=ValueError('factory')) if factory_error else lambda: protocol
    reader = ReaderThread(mock.Mock(), factory)
    try:
        reader.run()
    except ValueError:
        pass
    assert not reader.alive
    assert reader._connection_made.is_set()



def test_reader_can_stop_itself():
    from serial.threaded import ReaderThread, Protocol
    class StopProtocol(Protocol):
        def connection_made(self, transport):
            transport.stop()
        def connection_lost(self, error):
            errors.append(error)
    errors = []
    reader = ReaderThread(mock.Mock(), StopProtocol)
    reader.start()
    reader.join(2)
    assert not reader.is_alive()
    assert errors == [None]



@pytest.mark.parametrize('scheme', ['socket', 'rfc2217'])
@pytest.mark.parametrize('endpoint', ['localhost', ':1234'])
def test_network_url_requires_endpoint(scheme, endpoint):
    from serial.urlhandler import protocol_socket
    from serial import rfc2217
    handler = protocol_socket if scheme == 'socket' else rfc2217
    with pytest.raises(serial.SerialException):
        handler.Serial().from_url(scheme + '://' + endpoint)



@pytest.mark.parametrize('scheme', ['loop', 'socket', 'rfc2217'])
def test_invalid_url_logging_level(scheme):
    from serial.urlhandler import protocol_loop, protocol_socket
    from serial import rfc2217
    handler = {'loop': protocol_loop, 'socket': protocol_socket, 'rfc2217': rfc2217}[scheme]
    with pytest.raises(serial.SerialException):
        handler.Serial().from_url(scheme + '://localhost:1234?logging=invalid')

