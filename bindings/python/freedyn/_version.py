"""
FreeDyn version information.

The version is derived from the latest Git tag via setuptools-scm.
At build time (pip install / python -m build), setuptools-scm writes the
version into the installed package metadata. At runtime we read it back.

If running from a source checkout without installing, falls back to
setuptools-scm's get_version().
"""

try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("freedyn")
    except PackageNotFoundError:
        # Not installed – try setuptools-scm directly (dev scenario)
        from setuptools_scm import get_version
        __version__ = get_version(root="../../..", relative_to=__file__)
except Exception:
    __version__ = "0.0.0.dev0"
