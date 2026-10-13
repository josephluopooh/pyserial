"""Exercise HID serial behavior without requiring a CP2110 device."""
import importlib.util
from pathlib import Path
import queue
import sys
from unittest import mock
import pytest
import serial

@pytest.fixture
def backend():
    path = Path(serial.__file__).parent / 'urlhandler/protocol_cp2110.py'
    spec = importlib.util.spec_from_file_location('cp2110_test_backend', path)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {'hid': mock.Mock()}):
        spec.loader.exec_module(module)
    return module


def test_cp2110_close_is_idempotent(backend):
    port = backend.Serial()
    port.close()
    handle = mock.Mock()
    port._hid_handle = handle
    port.close()
    port.close()
    handle.close.assert_called_once_with()


def test_cp2110_failed_open_releases_handle(backend):
    handle = backend.hid.device.return_value
    handle.open_path.side_effect = OSError('unavailable')
    port = backend.Serial()
    port.port = 'cp2110:///dev/test'
    with pytest.raises(serial.SerialException):
        port.open()
    handle.close.assert_called_once_with()
    assert port._hid_handle is None
    port.close()



def test_cp2110_closed_input_count(backend):
    port = backend.Serial()
    with pytest.raises(serial.PortNotOpenError):
        _ = port.in_waiting

