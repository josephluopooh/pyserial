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

