"""
Internal utilities for ctypes operations and error handling.

Provides common patterns for calling C functions safely and converting
between C types and Python types.
"""

from ctypes import c_int, c_double, c_char_p, create_string_buffer, byref, POINTER
from typing import Optional, Any, Tuple
import numpy as np

from .exceptions import FreeDynError, DLLLoadError


def check_success(
    success_code: int,
    operation: str,
    error_buffer: Optional[str] = None,
    exception_class: type = FreeDynError
) -> None:
    """Check if a DLL operation succeeded and raise exception if not.
    
    Args:
        success_code: Return code from DLL function (typically 1 = success, <=0 = error)
        operation: Description of what operation failed (for error message)
        error_buffer: Optional error message from C code
        exception_class: Exception class to raise on failure
        
    Raises:
        exception_class: If success_code indicates failure
    """
    if success_code <= 0:
        msg = f"{operation} failed"
        if error_buffer:
            msg += f": {error_buffer}"
        raise exception_class(msg)


def call_c_function(
    dll,
    func_name: str,
    argtypes: Optional[list] = None,
    args: Optional[list] = None,
) -> Any:
    """Safely call a C function from the DLL with type checking.
    
    Args:
        dll: Loaded DLL object
        func_name: Name of the function to call
        argtypes: List of ctypes for argument types
        args: Arguments to pass to function
        
    Returns:
        Return value from the C function
    """
    if not dll:
        raise DLLLoadError("DLL not loaded. Call initialize() first.")
    
    func = getattr(dll, func_name)
    if argtypes:
        func.argtypes = argtypes
    
    if args:
        return func(*args)
    return func()


def encode_string(s: str) -> c_char_p:
    """Safely encode a Python string to ctypes c_char_p.
    
    Args:
        s: Python string
        
    Returns:
        ctypes c_char_p encoded string
    """
    return c_char_p(s.encode("utf-8"))


def decode_string(buffer: bytes) -> str:
    """Safely decode a ctypes string buffer to Python string.
    
    Args:
        buffer: Bytes from ctypes string buffer
        
    Returns:
        Decoded Python string
    """
    return buffer.decode("utf-8")


def create_error_buffer(size: int = 512) -> Tuple:
    """Create a buffer for error messages from C functions.
    
    Args:
        size: Buffer size (default 512 bytes)
        
    Returns:
        Tuple of (buffer, callable to decode buffer)
    """
    buf = create_string_buffer(size)
    return buf, lambda: decode_string(buf.value)
