"""
Unit tests for the input/output adapters.

This module contains tests for the platform-independent input and output
adapters that abstract away the differences between operating systems.
"""

import io
import os
import sys
import unittest
from unittest.mock import MagicMock, call, patch

from src.ui.adapters.io_adapter import (
    InputAdapter,
    OutputAdapter,
    UnixInputAdapter,
    WindowsInputAdapter,
    get_input_adapter,
)


class TestGetInputAdapter(unittest.TestCase):
    """Test cases for the get_input_adapter factory function."""

    @patch("src.ui.adapters.io_adapter.os.name", "nt")
    @patch("src.ui.adapters.io_adapter.WindowsInputAdapter")
    def test_get_windows_adapter(self, mock_windows_adapter):
        """Test getting a Windows input adapter."""
        # Setup
        mock_instance = MagicMock()
        mock_windows_adapter.return_value = mock_instance

        # Exercise
        adapter = get_input_adapter()

        # Verify
        self.assertEqual(adapter, mock_instance)
        mock_windows_adapter.assert_called_once()

    @patch("src.ui.adapters.io_adapter.os.name", "posix")
    @patch("src.ui.adapters.io_adapter.UnixInputAdapter")
    def test_get_unix_adapter(self, mock_unix_adapter):
        """Test getting a Unix input adapter."""
        # Setup
        mock_instance = MagicMock()
        mock_unix_adapter.return_value = mock_instance

        # Exercise
        adapter = get_input_adapter()

        # Verify
        self.assertEqual(adapter, mock_instance)
        mock_unix_adapter.assert_called_once()

    @patch("src.ui.adapters.io_adapter.os.name", "nt")
    @patch("src.ui.adapters.io_adapter.WindowsInputAdapter")
    def test_get_fallback_adapter_on_import_error(self, mock_windows_adapter):
        """Test falling back to a basic adapter on import error."""
        # Setup
        mock_windows_adapter.side_effect = ImportError("Module not found")

        # Exercise
        adapter = get_input_adapter()

        # Verify
        self.assertIsInstance(adapter, InputAdapter)
        mock_windows_adapter.assert_called_once()


class TestWindowsInputAdapter(unittest.TestCase):
    """Test cases for the WindowsInputAdapter class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Mock msvcrt
        self.msvcrt_patcher = patch("msvcrt")
        self.mock_msvcrt = self.msvcrt_patcher.start()

        # Create the adapter with the mocked msvcrt
        with patch("src.ui.adapters.io_adapter.msvcrt", self.mock_msvcrt):
            self.adapter = WindowsInputAdapter()

    def tearDown(self):
        """Tear down test fixtures after each test method."""
        self.msvcrt_patcher.stop()

    def test_read_char_available(self):
        """Test reading a character when one is available."""
        # Setup
        self.mock_msvcrt.kbhit.return_value = True
        self.mock_msvcrt.getwch.return_value = "a"

        # Exercise
        result = self.adapter.read_char()

        # Verify
        self.assertEqual(result, "a")
        self.mock_msvcrt.kbhit.assert_called_once()
        self.mock_msvcrt.getwch.assert_called_once()

    def test_read_char_not_available(self):
        """Test reading a character when none is available."""
        # Setup
        self.mock_msvcrt.kbhit.return_value = False

        # Exercise
        result = self.adapter.read_char()

        # Verify
        self.assertIsNone(result)
        self.mock_msvcrt.kbhit.assert_called_once()
        self.mock_msvcrt.getwch.assert_not_called()

    def test_read_line(self):
        """Test reading a line of input."""
        # Setup - simulate typing "hello" and then Enter
        self.mock_msvcrt.getwch.side_effect = ["h", "e", "l", "l", "o", "\r"]

        # Mock sys.stdout
        with patch("sys.stdout") as mock_stdout:
            # Exercise
            result = self.adapter.read_line()

            # Verify
            self.assertEqual(result, "hello")
            self.assertEqual(self.mock_msvcrt.getwch.call_count, 6)
            # Should write each character and a newline
            self.assertEqual(mock_stdout.write.call_count, 6)
            mock_stdout.flush.assert_called()


class TestUnixInputAdapter(unittest.TestCase):
    """Test cases for the UnixInputAdapter class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Mock required modules
        self.select_patcher = patch("select.select")
        self.mock_select = self.select_patcher.start()

        self.termios_patcher = patch("termios.tcgetattr")
        self.mock_tcgetattr = self.termios_patcher.start()

        self.termios_setattr_patcher = patch("termios.tcsetattr")
        self.mock_tcsetattr = self.termios_setattr_patcher.start()

        self.tty_patcher = patch("tty.setraw")
        self.mock_setraw = self.tty_patcher.start()

        # Mock settings
        self.mock_settings = MagicMock()
        self.mock_tcgetattr.return_value = self.mock_settings

        # Create the adapter with all mocks in place
        with (
            patch("src.ui.adapters.io_adapter.select.select", self.mock_select),
            patch("src.ui.adapters.io_adapter.termios.tcgetattr", self.mock_tcgetattr),
            patch("src.ui.adapters.io_adapter.termios.tcsetattr", self.mock_tcsetattr),
            patch("src.ui.adapters.io_adapter.tty.setraw", self.mock_setraw),
        ):
            self.adapter = UnixInputAdapter()

    def tearDown(self):
        """Tear down test fixtures after each test method."""
        self.select_patcher.stop()
        self.termios_patcher.stop()
        self.termios_setattr_patcher.stop()
        self.tty_patcher.stop()

    def test_read_char_available(self):
        """Test reading a character when one is available."""
        # Setup - simulate available input
        self.mock_select.return_value = ([sys.stdin], [], [])

        # Mock stdin.read
        with patch("sys.stdin.read") as mock_read:
            mock_read.return_value = "a"

            # Exercise
            result = self.adapter.read_char()

            # Verify
            self.assertEqual(result, "a")
            self.mock_select.assert_called_once()
            mock_read.assert_called_once_with(1)
            self.mock_setraw.assert_called_once()
            self.mock_tcsetattr.assert_called_once()

    def test_read_char_not_available(self):
        """Test reading a character when none is available."""
        # Setup - simulate no available input
        self.mock_select.return_value = ([], [], [])

        # Exercise
        result = self.adapter.read_char()

        # Verify
        self.assertIsNone(result)
        self.mock_select.assert_called_once()
        # Raw mode and reading should not happen
        self.mock_setraw.assert_not_called()

    def test_read_line(self):
        """Test reading a line of input."""
        # Setup
        test_input = "hello"

        # Mock input function
        with patch("builtins.input") as mock_input:
            mock_input.return_value = test_input

            # Exercise
            result = self.adapter.read_line()

            # Verify
            self.assertEqual(result, test_input)
            mock_input.assert_called_once()


class TestOutputAdapter(unittest.TestCase):
    """Test cases for the OutputAdapter class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.adapter = OutputAdapter()

    def test_write(self):
        """Test writing text output."""
        # Setup
        test_text = "This is a test message"

        # Mock sys.stdout
        with patch("sys.stdout") as mock_stdout:
            # Exercise
            self.adapter.write(test_text)

            # Verify
            mock_stdout.write.assert_called_once_with(test_text)
            mock_stdout.flush.assert_called_once()

    def test_clear_line_windows(self):
        """Test clearing a line on Windows."""
        # Setup - simulate Windows
        with patch("src.ui.adapters.io_adapter.os.name", "nt"):
            # Mock sys.stdout
            with patch("sys.stdout") as mock_stdout:
                # Exercise
                self.adapter.clear_line()

                # Verify - should use the Windows-specific approach
                mock_stdout.write.assert_called_once_with("\r" + " " * 80 + "\r")
                mock_stdout.flush.assert_called_once()

    def test_clear_line_unix(self):
        """Test clearing a line on Unix."""
        # Setup - simulate Unix
        with patch("src.ui.adapters.io_adapter.os.name", "posix"):
            # Mock sys.stdout
            with patch("sys.stdout") as mock_stdout:
                # Exercise
                self.adapter.clear_line()

                # Verify - should use the ANSI escape sequence
                mock_stdout.write.assert_called_once_with("\033[2K\r")
                mock_stdout.flush.assert_called_once()

    def test_move_cursor(self):
        """Test moving the cursor."""
        # Setup - simulate Unix (cursor movement uses ANSI, which is Unix-only)
        with patch("src.ui.adapters.io_adapter.os.name", "posix"):
            # Mock sys.stdout
            with patch("sys.stdout") as mock_stdout:
                # Exercise
                self.adapter.move_cursor(10, 5)

                # Verify
                mock_stdout.write.assert_called_once_with("\033[5;10H")
                mock_stdout.flush.assert_called_once()

    def test_set_title_windows(self):
        """Test setting the window title on Windows."""
        # Setup - simulate Windows
        with patch("src.ui.adapters.io_adapter.os.name", "nt"):
            # Mock ctypes.windll.kernel32.SetConsoleTitleW
            with patch("ctypes.windll.kernel32.SetConsoleTitleW") as mock_set_title:
                # Exercise
                self.adapter.set_title("Test Title")

                # Verify
                mock_set_title.assert_called_once_with("Test Title")

    def test_set_title_unix(self):
        """Test setting the window title on Unix."""
        # Setup - simulate Unix
        with patch("src.ui.adapters.io_adapter.os.name", "posix"):
            # Mock sys.stdout
            with patch("sys.stdout") as mock_stdout:
                # Exercise
                self.adapter.set_title("Test Title")

                # Verify - should use the appropriate escape sequence
                mock_stdout.write.assert_called_once_with("\033]0;Test Title\007")
                mock_stdout.flush.assert_called_once()

    def test_set_color(self):
        """Test setting text color."""
        # Setup - simulate Unix (color setting uses ANSI, which is Unix-only)
        with patch("src.ui.adapters.io_adapter.os.name", "posix"):
            # Mock sys.stdout
            with patch("sys.stdout") as mock_stdout:
                # Exercise - set foreground only
                self.adapter.set_color(31)  # Red foreground

                # Verify
                mock_stdout.write.assert_called_once_with("\033[31m")
                mock_stdout.flush.assert_called_once()

                # Reset mock
                mock_stdout.reset_mock()

                # Exercise - set foreground and background
                self.adapter.set_color(31, 42)  # Red on green

                # Verify
                mock_stdout.write.assert_called_once_with("\033[31;42m")
                mock_stdout.flush.assert_called_once()

    def test_reset_color(self):
        """Test resetting text color."""
        # Setup - simulate Unix (color resetting uses ANSI, which is Unix-only)
        with patch("src.ui.adapters.io_adapter.os.name", "posix"):
            # Mock sys.stdout
            with patch("sys.stdout") as mock_stdout:
                # Exercise
                self.adapter.reset_color()

                # Verify
                mock_stdout.write.assert_called_once_with("\033[0m")
                mock_stdout.flush.assert_called_once()


if __name__ == "__main__":
    unittest.main()
