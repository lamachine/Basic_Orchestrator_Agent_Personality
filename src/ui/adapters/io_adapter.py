"""
Platform-independent input/output adapters.

This module provides adapters for handling input and output operations
in a platform-independent way, abstracting away the differences between
operating systems.
"""

import os
import sys
from typing import Optional
from abc import ABC, abstractmethod

from src.services.logging_service import get_logger
logger = get_logger(__name__)

class InputAdapter(ABC):
    """
    Abstract base class for input adapters.
    
    This class provides a common interface for different input methods,
    allowing them to be used interchangeably.
    """
    
    @abstractmethod
    def read_char(self) -> Optional[str]:
        """
        Read a single character of input, non-blocking.
        
        Returns:
            The character read, or None if no input is available
        """
        pass
    
    @abstractmethod
    def read_line(self) -> str:
        """
        Read a full line of input, blocking until Enter is pressed.
        
        Returns:
            The line read
        """
        pass

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
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
    
    def read_char(self) -> Optional[str]:
        """
        Read a single character of input, non-blocking.
        
        Returns:
            The character read, or None if no input is available
        """
        try:
            if self.select.select([sys.stdin], [], [], 0)[0]:
                self.tty.setraw(self.fd)
                char = sys.stdin.read(1)
                return char
        finally:
            self.termios.tcsetattr(self.fd, self.termios.TCSADRAIN, self.old_settings)
        return None
    
    def read_line(self) -> str:
        """
        Read a full line of input, blocking until Enter is pressed.
        
        Returns:
            The line read
        """
        return input()

def get_input_adapter() -> InputAdapter:
    """
    Get the appropriate input adapter for the current platform.
    
    Returns:
        An InputAdapter instance for the current platform
    """
    if os.name == 'nt':
        try:
            return WindowsInputAdapter()
        except ImportError:
            logger.warning("Failed to import msvcrt. Falling back to default input")
    else:
        try:
            return UnixInputAdapter()
        except ImportError:
            logger.warning("Failed to import Unix-specific modules. Falling back to default input")
    class FallbackInputAdapter(InputAdapter):
        def read_char(self) -> Optional[str]:
            return None
        def read_line(self) -> str:
            return input()
    return FallbackInputAdapter()

class OutputAdapter(ABC):
    """
    Abstract base class for output operations.
    
    This class defines the interface for displaying text output in a
    platform-independent way.
    """
    
    @abstractmethod
    def write(self, text: str) -> None:
        """
        Write text to the output.
        
        Args:
            text: The text to write
        """
        pass
    
    @abstractmethod
    def clear_line(self) -> None:
        """
        Clear the current line of output.
        """
        pass
    
    @abstractmethod
    def move_cursor(self, x: int, y: int) -> None:
        """
        Move the cursor to the specified position.
        
        Args:
            x: The column to move to
            y: The row to move to
        """
        pass
    
    @abstractmethod
    def set_title(self, title: str) -> None:
        """
        Set the title of the terminal window.
        
        Args:
            title: The new title
        """
        pass
    
    @abstractmethod
    def set_color(self, foreground: int, background: int = None) -> None:
        """
        Set the text color.
        
        Args:
            foreground: The foreground color code
            background: The background color code (optional)
        """
        pass
    
    @abstractmethod
    def reset_color(self) -> None:
        """
        Reset the text color to default.
        """
        pass

class TerminalOutputAdapter(OutputAdapter):
    """Concrete implementation of OutputAdapter for terminal output."""
    
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
        if os.name == 'nt':
            sys.stdout.write('\r' + ' ' * 80 + '\r')
        else:
            sys.stdout.write('\033[2K\r')
        sys.stdout.flush()
    
    def move_cursor(self, x: int, y: int) -> None:
        """
        Move the cursor to the specified position.
        
        Args:
            x: The column to move to
            y: The row to move to
        """
        if os.name != 'nt':
            sys.stdout.write(f"\033[{y};{x}H")
            sys.stdout.flush()
    
    def set_title(self, title: str) -> None:
        """
        Set the title of the terminal window.
        
        Args:
            title: The new title
        """
        if os.name == 'nt':
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        else:
            sys.stdout.write(f"\033]0;{title}\007")
            sys.stdout.flush()
    
    def set_color(self, foreground: int, background: int = None) -> None:
        """
        Set the text color.
        
        Args:
            foreground: The foreground color code
            background: The background color code (optional)
        """
        if os.name != 'nt':
            if background is not None:
                sys.stdout.write(f"\033[{foreground};{background}m")
            else:
                sys.stdout.write(f"\033[{foreground}m")
            sys.stdout.flush()
    
    def reset_color(self) -> None:
        """Reset the text color to default."""
        if os.name != 'nt':
            sys.stdout.write("\033[0m")
            sys.stdout.flush() 