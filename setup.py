from setuptools import setup, find_packages, Distribution
import glob
import os
import shutil


class BinaryDistribution(Distribution):
    """Force platform-specific wheel (win_amd64) because we ship native DLLs."""
    def has_ext_modules(self):
        return True


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Copy DLLs from top-level bin/x64_MD/ into the package so they are included
# in wheels. Python must use the MD (dynamic CRT) variant.
# Exclude GUI-only DLLs (wxWidgets, image libs) to keep wheel under PyPI 100 MB limit.
_GUI_ONLY_DLLS = {
    "wxbase32u_vc_x64_custom.dll",
    "wxmsw32u_core_vc_x64_custom.dll",
    "jpeg62.dll",
    "libpng16.dll",
    "liblzma.dll",
    "pcre2-16.dll",
    "tiff.dll",
    "zlib1.dll",
}
_top_bin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "x64_MD")
_pkg_bin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "bindings", "python", "freedyn", "bin")
if os.path.isdir(_top_bin):
    os.makedirs(_pkg_bin, exist_ok=True)
    for _src in glob.glob(os.path.join(_top_bin, "*.dll")):
        if os.path.basename(_src).lower() not in {d.lower() for d in _GUI_ONLY_DLLS}:
            shutil.copy2(_src, _pkg_bin)

setup(
    name="freedyn",
    use_scm_version=True,
    setup_requires=["setuptools-scm"],
    author="FreeDyn Team",
    description="Python bindings for FreeDyn Multi-Body System (MBS) simulator - Windows only",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/freedyn-org/freedyn",
    license="LGPL-3.0",
    distclass=BinaryDistribution,
    package_dir={"": "bindings/python"},
    packages=find_packages(where="bindings/python"),
    include_package_data=True,
    package_data={
        "freedyn": ["bin/*.dll"],
    },
    entry_points={
        "console_scripts": [
            "freedyn-run=freedyn.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Microsoft :: Windows :: Windows 7",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Operating System :: Microsoft :: Windows :: Windows 11",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy",
        "scipy",
    ],
    extras_require={
        "dev": [
            "pytest",
            "matplotlib",  # For visualization examples
        ],
    },
)
