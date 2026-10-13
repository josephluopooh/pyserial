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

