# print3d-skill Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-14

## Active Technologies

- Python 3.10+ (001-core-infrastructure)
- trimesh (mesh I/O), manifold3d (boolean CSG), numpy, matplotlib, Pillow, PyYAML

## Project Structure

```text
src/print3d_skill/          # Main package (src layout)
tests/                      # pytest test suite
knowledge_base/             # Bundled YAML knowledge files (package data)
```

## Commands

```bash
pip install -e ".[dev]"     # Install in dev mode
pytest                      # Run tests
pytest --cov=print3d_skill  # Run tests with coverage
ruff check src/ tests/      # Lint
ruff format src/ tests/     # Format
```

## Code Style

Python 3.10+: type hints required, dataclasses for models, src layout

## Recent Changes

- 001-core-infrastructure: foundational rendering, tool orchestration, knowledge system, skill router

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
