"""Linux port discovery regressions using a synthetic sysfs tree."""

import sys

import pytest

if not sys.platform.startswith('linux'):
    pytest.skip('Linux sysfs tests', allow_module_level=True)

from serial.tools.list_ports_linux import SysFS


@pytest.fixture
def usb_device(fs):
    root = '/sys/devices/usb1/1-1'
    interface = root + '/1-1:1.0'
    fs.create_dir(interface)
    fs.create_symlink(interface + '/subsystem', '/sys/bus/usb')
    fs.create_symlink('/sys/class/tty/ttyACM0/device', interface)
    fs.create_file('/dev/ttyACM0')
    for name, value in {'bNumInterfaces': '1', 'idVendor': '1234',
                        'idProduct': '5678', 'product': 'Test device'}.items():
        fs.create_file(root + '/' + name, contents=value)
    return root


@pytest.mark.parametrize('attribute', ['bNumInterfaces', 'idVendor', 'idProduct'])
@pytest.mark.parametrize('value', [None, '', 'invalid'])
def test_missing_usb_numeric_attributes(fs, usb_device, attribute, value):
    path = usb_device + '/' + attribute
    fs.remove_object(path)
    if value is not None:
        fs.create_file(path, contents=value)
    info = SysFS('/dev/ttyACM0')
    assert info.description == 'Test device'
    if attribute == 'bNumInterfaces':
        assert info.location == '1-1'
    else:
        assert getattr(info, 'vid' if attribute == 'idVendor' else 'pid') is None


def test_symlink_retains_usb_metadata(fs, usb_device):
    fs.create_symlink('/dev/serial/by-id/example', '/dev/ttyACM0')
    info = SysFS('/dev/serial/by-id/example')
    assert info.device == '/dev/serial/by-id/example'
    assert info.description == 'Test device'
    assert info.vid == 0x1234
    assert info.pid == 0x5678
    assert 'LINK=/dev/ttyACM0' in info.hwid
