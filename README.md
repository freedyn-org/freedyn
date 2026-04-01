# FreeDyn

**Multi-Body System (MBS) Simulation and Analysis Software**

## What is FreeDyn?

FreeDyn is a powerful simulation software for modeling and analyzing Multi-Body Systems (MBS). It supports:

- **Rigid and flexible body dynamics** with arbitrary kinematic structures
- **Advanced constraint modeling** (joints, contact, etc.)
- **Multiple force models** (springs, dampers, external forces, etc.)
- **HHT time integration solver** for implicit integration
- **Python/MATLAB/Scilab interfaces** for custom analysis
- **GUI and command-line tools** for pre- and post-processing

## Download

Download the latest release as a ZIP archive from **[GitHub Releases](https://github.com/freedyn-org/freedyn/releases)**.

## Documentation

- [Getting Started](docs/GETTING_STARTED.md) - Installation and first steps (GUI & Python)
- [Examples](examples/) - Python code examples and tutorials
- [Release Notes](#release-notes) - What's new

## Quick Start

### Option A – GUI (no programming required)

1. Download and extract the release ZIP
2. Run **`bin\x64_MD\Freedyn_GUI.exe`** from the extracted folder
3. Open a model file (`.fds`) and start simulating

No Python or other tools required.

### Option B – Python Scripting

For automated simulations, custom analysis, and batch processing:

1. Install the Python bindings from the extracted release directory:
   ```bash
   cd C:\FreeDyn
   pip install .
   ```
2. Run a model from the command line:
   ```bash
   freedyn-run path/to/model.fds
   ```
3. Or script it:
   ```python
   import freedyn as fd

   fd.initialize()  # loads freedyn.dll
   with fd.Model("path/to/model.fds") as model:
      model.solve()
      for idx, time, states in model.iterate_time_steps():
         print(idx, time, states["Q"][0, 0])
   ```

More detail: [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)

## Features

### Simulation Capabilities
- Kinematic and dynamic analysis
- Time-domain simulation with implicit integration
- Automatic constraint handling
- Flexible body dynamics
- Contact models

### Analysis Tools
- **Jacobian extraction** - System matrices at any time point
- **Force/motion analysis** - Extract forces, accelerations, constraint forces
- **Parameter sensitivity** - Analytical jacobians w.r.t. parameters
- **Custom measures** - User-defined outputs

### Integration Options
- **GUI** - Pre- and post-processing with `Freedyn_GUI.exe`
- **Python API** - Programmatic simulation and analysis
- **MATLAB API** - Scripting via `freedyn_api.m` + Simulink integration
- **Scilab API** - Scripting via `freedyn_api.sce` (uses MT variant)
- **C interface (CDLL)** - Direct DLL linking for other languages

## Architecture

FreeDyn consists of several components:

- **Freedyn_GUI.exe** - Graphical pre- and post-processor
- **freedyn.dll** - Core MBS solver (C-interface Dynamic Link Library)
- **Python bindings** - High-level API for scripting and analysis (open source)
- **CLI tool** - Command-line interface (`freedyn-run`)

## Requirements

### GUI / Standalone Use
- Windows 7 or later (64-bit)
- Visual C++ Redistributable (included in release)
- Intel MKL runtime (included in release)

### Python Bindings (optional)
- Python 3.8+
- numpy, scipy

## License

FreeDyn is released under the GNU Lesser General Public License v3.

The Python bindings (source code in this repository) are open source.
The binary components (`freedyn.dll`, `Freedyn_GUI.exe`, etc.) are distributed
as pre-built binaries via [GitHub Releases](https://github.com/freedyn-org/freedyn/releases).

See [LICENSE](LICENSE) for details.

## Support & Issues

- **GitHub Issues**: [Report bugs](https://github.com/freedyn-org/freedyn/issues)
- **Documentation**: See [docs/](docs/) folder
- **Examples**: See [examples/](examples/) folder

## Release Notes

**Latest Release**
- Initial public release
- Complete Python bindings refactoring
- High-level API (Model, ModelInfo, analysis functions)
- Command-line tool (freedyn-run)
- Core MBS simulation capabilities
- Matrix/vector extraction functionality
- Comprehensive documentation

## Contributing

Contributions to the Python bindings are welcome:

1. Check existing [issues](https://github.com/freedyn-org/freedyn/issues)
2. Follow the coding guidelines
3. Submit pull requests with clear descriptions

## Citation

If you use FreeDyn in your research, please cite:

```bibtex
@software{freedyn2025,
  title = {FreeDyn: Multi-Body System Simulation Software},
  author = {Oberpeilsteiner, Stefan and others},
  year = {2025},
  url = {https://github.com/freedyn-org/freedyn}
}
```

## Author

**Stefan Oberpeilsteiner** (FreeDyn Development Team)

---

**Repository**: https://github.com/freedyn-org/freedyn  
**Version**: See [_version.py](bindings/python/freedyn/_version.py) for current version
