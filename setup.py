from setuptools import setup, find_packages

# Read version from _version.py
import re
with open("bindings/python/freedyn/_version.py") as f:
    version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="freedyn",
    version=version,
    author="FreeDyn Team",
    description="Python bindings for FreeDyn Multi-Body System (MBS) simulator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/freedyn-org/freedyn",
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
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Operating System :: Microsoft :: Windows",
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
