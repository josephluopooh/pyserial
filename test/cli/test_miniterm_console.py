"""Exercise POSIX console cancellation without terminal input injection."""

import atexit
import io
import os
import signal
import queue
import threading
import unittest
from unittest import mock

try:
    import pty
except ImportError:
    pty = None


@unittest.skipIf(pty is None, 'requires POSIX pseudo terminals')
class TestConsole(unittest.TestCase):
    def setUp(self):
        # miniterm registers a process-wide codec at import time. Keep that
        # unrelated side effect out of these console tests.
        with mock.patch('codecs.register'):
            from serial.tools import miniterm

        master, slave = pty.openpty()
        self.master = master
        self.addCleanup(os.close, master)
        self.stdin = io.open(slave, 'r', encoding='utf-8', errors='surrogateescape')
        self.addCleanup(self.stdin.close)
        self.addCleanup(signal.signal, signal.SIGINT, signal.getsignal(signal.SIGINT))
        stdout = io.TextIOWrapper(io.BytesIO(), encoding='utf-8')
        self.addCleanup(stdout.close)
        with mock.patch('sys.stdin', self.stdin), mock.patch('sys.stdout', stdout):
            self.console = miniterm.Console(mock.Mock())
        self.addCleanup(atexit.unregister, self.console.cleanup)
        self.addCleanup(self.cleanup_console)
        self.console.setup()

    def cleanup_console(self):
        if hasattr(self.console, 'close'):
            self.console.close()
        else:
            self.console.cleanup()

    def test_cancel_without_tiocsti(self):
        # This kernel rejects TIOCSTI, as do WSL and modern Linux defaults.
        # Cancellation must not rely on injecting bytes into the terminal.
        with mock.patch('fcntl.ioctl', side_effect=OSError('TIOCSTI unavailable')):
            self.console.cancel()
            self.assertEqual(self.console.getkey(), '\0')

    def test_unicode_and_escape_sequences(self):
        text = '\N{SNOWMAN}\x1b[A\N{LATIN SMALL LETTER E WITH ACUTE}'
        os.write(self.master, text.encode('utf-8'))
        self.assertEqual(''.join(self.console.getkey() for _ in text), text)

    def test_repeated_cancellation(self):
        for _ in range(3):
            self.console.cancel()
            self.assertEqual(self.console.getkey(), '\0')
        os.write(self.master, b'x')
        self.assertEqual(self.console.getkey(), 'x')

    def test_backspace(self):
        os.write(self.master, b'\x7f')
        self.assertEqual(self.console.getkey(), '\x08')

    def test_cancel_incomplete_unicode_character(self):
        from serial.tools import miniterm

        entered_second_select = threading.Event()
        results = queue.Queue()
        select_call = miniterm.select.select
        calls = []

        def observe_select(*args):
            calls.append(None)
            if len(calls) == 2:
                entered_second_select.set()
            return select_call(*args)

        def read_key():
            try:
                results.put(self.console.getkey())
            except Exception as error:
                results.put(error)

        encoded = '\N{SNOWMAN}'.encode('utf-8')
        os.write(self.master, encoded[:1])
        reader = threading.Thread(target=read_key, daemon=True)
        with mock.patch.object(miniterm.select, 'select', side_effect=observe_select):
            reader.start()
            try:
                self.assertTrue(entered_second_select.wait(1))
                self.console.cancel()
                self.assertEqual(results.get(timeout=1), '\0')
            finally:
                # Always finish the incomplete character, even on failure, so
                # the helper cannot remain blocked on a failed assertion.
                os.write(self.master, encoded[1:])
                reader.join(1)
        self.assertFalse(reader.is_alive())
        self.assertEqual(self.console.getkey(), '\N{SNOWMAN}')

    def test_close_releases_cancellation_sockets(self):
        self.console.close()
        self.assertEqual(self.console._cancel_reader.fileno(), -1)
        self.assertEqual(self.console._cancel_writer.fileno(), -1)

    def test_cleanup_then_setup_preserves_console_use(self):
        self.console.cleanup()
        self.console.setup()
        os.write(self.master, b'x')
        self.assertEqual(self.console.getkey(), 'x')
