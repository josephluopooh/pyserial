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
