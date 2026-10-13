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



@pytest.mark.parametrize('length', [0, 1, 63, 64, 127])
def test_cp2110_write_count(backend, length):
    port = backend.Serial()
    port.is_open = True
    port._hid_handle = mock.Mock()
    port._hid_handle.write.side_effect = len
    try:
        assert port.write(b'x' * length) == length
    finally:
        port.close()



def test_cp2110_read_size_and_waiting_bytes(backend):
    port = backend.Serial(timeout=0)
    port.is_open = True
    port._read_buffer = queue.Queue()
    port._hid_handle = mock.Mock()
    def receive(*args, **kwargs):
        port.is_open = False
        return [3, 65, 66, 67]
    port._hid_handle.read.side_effect = receive
    port._hid_read_loop()
    port.is_open = True
    port._thread = mock.Mock()
    try:
        assert port.in_waiting == 3
        assert port.read(2) == b'AB'
        assert port.in_waiting == 1
        assert port.read(5) == b'C'
    finally:
        port._thread = None
        port.close()



def test_cp2110_short_hid_write(backend):
    port = backend.Serial()
    port.is_open = True
    port._hid_handle = mock.Mock()
    port._hid_handle.write.return_value = 1
    try:
        with pytest.raises(serial.SerialException, match='short'):
            port.write(b'abc')
    finally:
        port.close()



def test_cp2110_failed_reader_wakes_pending_read(backend):
    import threading
    port = backend.Serial()
    port.is_open = True
    port._read_buffer = queue.Queue()
    port._hid_handle = mock.Mock()
    port._hid_handle.read.side_effect = OSError('disconnected')
    port._thread = mock.Mock()
    waiting = threading.Event()
    original_get = port._read_buffer.get
    def get(*args, **kwargs):
        waiting.set()
        return original_get(*args, **kwargs)
    port._read_buffer.get = get
    result = []
    reader = threading.Thread(target=lambda: result.append(port.read(1)), daemon=True)
    reader.start()
    assert waiting.wait(1)
    try:
        with pytest.raises(OSError):
            port._hid_read_loop()
        reader.join(1)
        assert not reader.is_alive()
        assert result == [b'']
    finally:
        port._read_buffer.put(None)
        reader.join(1)
        port.close()

