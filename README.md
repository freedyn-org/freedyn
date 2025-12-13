# FreeDyn v1.0.0

**Multi-Body System (MBS) Simulation and Analysis Software**

## What is FreeDyn?

FreeDyn is a powerful simulation software for modeling and analyzing Multi-Body Systems (MBS). It supports:

- **Rigid and flexible body dynamics** with arbitrary kinematic structures
- **Advanced constraint modeling** (joints, contact, etc.)
- **Multiple force models** (springs, dampers, external forces, etc.)
- **HHT time integration solver** for implicit integration
- **Python/MATLAB/Scilab interfaces** for custom analysis
- **GUI and command-line tools** for pre- and post-processing

## Documentation

- [Getting Started](docs/GETTING_STARTED.md) - Installation and first steps
- [Examples](examples/) - Code examples and tutorials
- [Release Notes](#release-notes) - Version history

## Quick Start (Python)

1. Install from the extracted release directory:
  ```bash
  pip install .
  ```
2. Run a model from the CLI:
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
- **Python API** - Programmatic simulation and analysis
- **MATLAB interface** - Integration with MATLAB workflows
- **Scilab interface** - Open-source alternative to MATLAB
- **C interface (CDLL)** - Direct DLL linking for other languages

## Architecture

FreeDyn consists of several core components:

- **freedyn.dll** - C-interface Dynamic Link Library (core solver)
- **fdApi** - Python wrapper with convenience functions
- **fdApi2** - Advanced functions (matrices, vectors)
- **GUI/CLI tools** - Pre- and post-processing

## Requirements

### Runtime
- Windows (tested on Windows 7, 10, 11)
- Visual C++ Redistributable (included in release)
- Intel MKL library (included in release)

### Development (for bindings)
- Python 3.8+
- numpy
- scipy

## License

FreeDyn v1.0.0 is released under the GNU Lesser General Public License v3.

See [LICENSE](LICENSE) for details.

## Support & Issues

- **GitHub Issues**: [Report bugs](https://github.com/freedyn-org/freedyn/issues)
- **Documentation**: See [docs/](docs/) folder
- **Examples**: See [examples/](examples/) folder

## Version History

### v1.0.0 (December 2025)
- Initial public release
- Python bindings (fdApi, fdApi2)
- Core MBS simulation capabilities
- Matrix/vector extraction functionality
- 3 example scripts

## Contributing

To contribute to FreeDyn, please:

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
**Release**: v1.0.0  
**Date**: December 2025
