"""
Platform-independent input/output adapters.

This module provides adapters for handling input and output operations
in a platform-independent way, abstracting away the differences between
operating systems.
"""

import os
import sys
import time
import logging
from typing import Optional, Callable, Any

# Setup logging
from src.services.logging_services.logging_service import get_logger
logger = get_logger(__name__)

class InputAdapter:
    """
    Abstract base class for input adapters.
    
    This class provides a common interface for different input methods,
    allowing them to be used interchangeably.
    """
    
    def read_char(self) -> Optional[str]:
        """
        Read a single character of input, non-blocking.
        
        Returns:
            The character read, or None if no input is available
        """
        raise NotImplementedError("Subclasses must implement read_char")
    
    def read_line(self) -> str:
        """
        Read a full line of input, blocking until Enter is pressed.
        
        Returns:
            The line read
        """
        raise NotImplementedError("Subclasses must implement read_line")

class WindowsInputAdapter(InputAdapter):
    """Input adapter for Windows systems."""
    
    def __init__(self):
        """Initialize the Windows input adapter."""
        import msvcrt
        self.msvcrt = msvcrt
    
    def read_char(self) -> Optional[str]:
        """
        Read a single character of input, non-blocking.
        
        Returns:
            The character read, or None if no input is available
        """
        if self.msvcrt.kbhit():
            return self.msvcrt.getwch()
        return None
    
    def read_line(self) -> str:
        """
        Read a full line of input, blocking until Enter is pressed.
        
        Returns:
            The line read
        """
        buffer = ""
        while True:
            char = self.msvcrt.getwch()
            if char == '\r':  # Enter key
                sys.stdout.write('\n')
                sys.stdout.flush()
                return buffer
            elif char == '\b':  # Backspace
                if buffer:
                    buffer = buffer[:-1]
                    sys.stdout.write('\b \b')  # Erase the character
                    sys.stdout.flush()
            else:
                buffer += char
                sys.stdout.write(char)
                sys.stdout.flush()

class UnixInputAdapter(InputAdapter):
    """Input adapter for Unix/Linux/MacOS systems."""
    
    def __init__(self):
        """Initialize the Unix input adapter."""
        import select
        import termios
        import tty
        self.select = select
        self.termios = termios
        self.tty = tty
        
        # Save terminal settings
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
    
    def read_char(self) -> Optional[str]:
        """
        Read a single character of input, non-blocking.
        
        Returns:
            The character read, or None if no input is available
        """
        try:
            # Use select to check if input is available
            if self.select.select([sys.stdin], [], [], 0)[0]:
                # Set terminal to raw mode
                self.tty.setraw(self.fd)
                char = sys.stdin.read(1)
                return char
        finally:
            # Restore terminal settings
            self.termios.tcsetattr(self.fd, self.termios.TCSADRAIN, self.old_settings)
        
        return None
    
    def read_line(self) -> str:
        """
        Read a full line of input, blocking until Enter is pressed.
        
        Returns:
            The line read
        """
        # Use Python's built-in input function, which works on all platforms
        return input()

def get_input_adapter() -> InputAdapter:
    """
    Get the appropriate input adapter for the current platform.
    
    Returns:
        An InputAdapter instance for the current platform
    """
    if os.name == 'nt':  # Windows
        try:
            return WindowsInputAdapter()
        except ImportError:
            logger.warning("Failed to import msvcrt. Falling back to default input")
    else:  # Unix/Linux/MacOS
        try:
            return UnixInputAdapter()
        except ImportError:
            logger.warning("Failed to import Unix-specific modules. Falling back to default input")
    
    # If we get here, we couldn't create a platform-specific adapter
    # Fall back to a simple adapter that uses input() and doesn't do non-blocking
    class FallbackInputAdapter(InputAdapter):
        def read_char(self) -> Optional[str]:
            return None  # Non-blocking not supported
        
        def read_line(self) -> str:
            return input()
    
    return FallbackInputAdapter()

class OutputAdapter:
    """
    Adapter for output operations.
    
    This class provides methods for displaying text output in a
    platform-independent way.
    """
    
    def write(self, text: str) -> None:
        """
        Write text to the output.
        
        Args:
            text: The text to write
        """
        sys.stdout.write(text)
        sys.stdout.flush()
    
    def clear_line(self) -> None:
        """Clear the current line of output."""
        if os.name == 'nt':  # Windows
            sys.stdout.write('\r' + ' ' * 80 + '\r')  # Erase the line
        else:  # Unix/Linux/MacOS
            sys.stdout.write('\033[2K\r')  # ANSI escape sequence to clear line
        sys.stdout.flush()
    
    def move_cursor(self, x: int, y: int) -> None:
        """
        Move the cursor to the specified position.
        
        Args:
            x: The column to move to
            y: The row to move to
        """
        if os.name != 'nt':  # This only works on Unix/Linux/MacOS
            sys.stdout.write(f"\033[{y};{x}H")
            sys.stdout.flush()
    
    def set_title(self, title: str) -> None:
        """
        Set the title of the terminal window.
        
        Args:
            title: The new title
        """
        if os.name == 'nt':  # Windows
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        else:  # Unix/Linux/MacOS
            sys.stdout.write(f"\033]0;{title}\007")
            sys.stdout.flush()
    
    def set_color(self, foreground: int, background: int = None) -> None:
        """
        Set the text color.
        
        Args:
            foreground: The foreground color code
            background: The background color code (optional)
        """
        if os.name != 'nt':  # This only works on Unix/Linux/MacOS with ANSI support
            if background is not None:
                sys.stdout.write(f"\033[{foreground};{background}m")
            else:
                sys.stdout.write(f"\033[{foreground}m")
            sys.stdout.flush()
    
    def reset_color(self) -> None:
        """Reset the text color to default."""
        if os.name != 'nt':  # This only works on Unix/Linux/MacOS with ANSI support
            sys.stdout.write("\033[0m")
            sys.stdout.flush() 