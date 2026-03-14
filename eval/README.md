# Evaluation Use Cases

Real-world scenarios for testing the Print3D Skill end-to-end once modes are implemented. Each subdirectory is a self-contained case with mesh assets, a description of the problem, and expected skill behavior.

## Structure

```
eval/
├── README.md
├── 001-resize-headset-holder/
│   ├── README.md          # Problem description, constraints, expected outcome
│   └── assets/            # STL/3MF/OBJ/SCAD files
└── 002-next-case/
    ├── README.md
    └── assets/
```

## Adding a New Use Case

1. Create `eval/NNN-short-name/` with the next available number
2. Add a `README.md` describing: what happened, what you want the skill to do, and any constraints
3. Drop mesh files into `assets/`

## Use Case Index

| # | Name | Mode(s) | Status |
|---|------|---------|--------|
| 001 | [Resize Headset Holder](001-resize-headset-holder/) | Modify | Ready (F4 complete) |
