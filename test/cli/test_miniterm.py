"""Regression tests for miniterm's interactive error handling."""

from unittest import mock

import pytest

# Importing the CLI must not register a codec for unrelated codec tests.
with mock.patch('codecs.register'):
    from serial.tools import miniterm


def test_eof_at_initial_port_prompt():
    with mock.patch.object(miniterm.sys, 'argv', ['miniterm']), \
            mock.patch.object(miniterm, 'ask_for_port', side_effect=EOFError):
        with pytest.raises(SystemExit) as error:
            miniterm.main()
    assert error.value.code == 2


def test_eof_cancels_port_change():
    terminal = object.__new__(miniterm.Miniterm)
    terminal.console = mock.MagicMock()
    terminal.serial = mock.Mock()
    with mock.patch.object(miniterm, 'ask_for_port', side_effect=EOFError):
        terminal.change_port()
    terminal.serial.close.assert_not_called()


def test_unsupported_url_keeps_existing_port():
    terminal = object.__new__(miniterm.Miniterm)
    terminal.console = mock.MagicMock()
    terminal.serial = mock.Mock()
    terminal._stop_reader = mock.Mock()
    terminal._start_reader = mock.Mock()
    with mock.patch.object(miniterm, 'ask_for_port', return_value='unsupported://'):
        terminal.change_port()
    terminal.serial.close.assert_not_called()
    terminal._start_reader.assert_called_once_with()


def test_exit_while_port_suspended():
    terminal = object.__new__(miniterm.Miniterm)
    terminal.serial = mock.Mock(is_open=False, port='test')
    terminal.console = mock.Mock()
    terminal.exit_character = '\x1d'
    terminal.console.getkey.return_value = terminal.exit_character
    terminal._stop_reader = mock.Mock()
    terminal._start_reader = mock.Mock()
    terminal.stop = mock.Mock()
    terminal.suspend_port()
    terminal.stop.assert_called_once_with()
    terminal._start_reader.assert_not_called()



def test_writer_console_eof():
    terminal = object.__new__(miniterm.Miniterm)
    terminal.alive = True
    terminal.console = mock.Mock()
    terminal.console.getkey.side_effect = ['', AssertionError('read beyond EOF')]
    terminal.serial = mock.Mock()
    terminal.menu_character = '\x14'
    terminal.exit_character = '\x1d'
    terminal.tx_transformations = []
    terminal.tx_encoder = mock.Mock()
    terminal.echo = False
    terminal.writer()
    assert not terminal.alive
    terminal.serial.write.assert_not_called()



@pytest.mark.parametrize('direction', ['rx', 'tx'])
def test_invalid_encoding_preserves_current_codec(direction):
    terminal = object.__new__(miniterm.Miniterm)
    setter = getattr(terminal, 'set_' + direction + '_encoding')
    setter('utf-8')
    field = 'input_encoding' if direction == 'rx' else 'output_encoding'
    old = getattr(terminal, field)
    with pytest.raises(LookupError):
        setter('not-a-real-encoding')
    assert getattr(terminal, field) == old



def test_upload_retries_partial_writes(tmp_path):
    import io
    filename = tmp_path / 'upload.bin'
    filename.write_bytes(b'abcdef')
    terminal = object.__new__(miniterm.Miniterm)
    terminal.console = mock.MagicMock()
    terminal.serial = mock.Mock()
    terminal.serial.write.side_effect = [2, 4]
    with mock.patch.object(miniterm.sys, 'stdin', io.StringIO(str(filename) + '\n')):
        terminal.upload_file()
    assert terminal.serial.write.call_args_list == [mock.call(b'abcdef'), mock.call(b'cdef')]



def test_unknown_filter_fails_before_opening_port():
    with mock.patch.object(miniterm.sys, 'argv', ['miniterm', 'loop://', '--filter', 'missing-filter']), \
            mock.patch.object(miniterm.serial, 'serial_for_url') as open_port:
        with pytest.raises(SystemExit) as error:
            miniterm.main()
    assert error.value.code == 2
    open_port.assert_not_called()
