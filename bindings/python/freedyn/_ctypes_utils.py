"""
Internal utilities for ctypes operations and error handling.

Provides common patterns for calling C functions safely and converting
between C types and Python types.
"""

from ctypes import c_int, c_double, c_char_p, create_string_buffer, byref, POINTER
from typing import Optional, Tuple
import numpy as np

from .exceptions import FreeDynError


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


def as_ptr(array: np.ndarray, ctype, min_size: Optional[int] = None):
    """Return a ctypes pointer to the data of a numpy array.

    Replaces np.ctypeslib.ndpointer argtypes: the checks run once here instead of
    on every DLL call, so hot paths can create the pointer once and reuse it.
    The returned pointer keeps a reference to the array.

    Args:
        array: Numpy array passed to the DLL
        ctype: Expected element type (c_int or c_double)
        min_size: Minimum number of elements the DLL may access

    Returns:
        POINTER(ctype) to the first element

    Raises:
        TypeError: If dtype does not match or the data is not contiguous
        ValueError: If the array has fewer than min_size elements
    """
    if not isinstance(array, np.ndarray):
        raise TypeError(f"expected numpy.ndarray, got {type(array).__name__}")
    if array.dtype != np.dtype(ctype):
        raise TypeError(f"array dtype must be {np.dtype(ctype)}, got {array.dtype}")
    if not (array.flags.c_contiguous or array.flags.f_contiguous):
        raise TypeError("array must be contiguous in memory")
    if min_size is not None and array.size < min_size:
        raise ValueError(f"array has {array.size} elements, DLL expects at least {min_size}")
    return array.ctypes.data_as(POINTER(ctype))


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
