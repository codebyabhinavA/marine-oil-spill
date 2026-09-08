# Contributing (team workflow)

## Before you write any code

Read [docs/API_CONTRACT.md](docs/API_CONTRACT.md). It defines the exact
JSON every module reads and writes. As long as your module respects the
contract for its stage, you can change absolutely everything about how
it works internally without breaking anyone else's code or causing merge
conflicts in shared files.

## Branching

Don't push straight to `main`. For each piece of work:

```bash
git checkout main
git pull
git checkout -b feature/<your-module>-<short-description>
# e.g. feature/m4-ais-real-feed, feature/m2-cnn-detector
```

Work inside your module's folder (`backend/satellite/`,
`backend/drift/`, `backend/ais/`, `backend/attribution/`, or
`frontend/`). That folder boundary is what keeps everyone's changes from
colliding — two people editing `backend/main.py` or `docs/API_CONTRACT.md`
at the same time is the one thing worth pinging the team about first.

## Committing

```bash
git add .
git commit -m "type: short description"
```
Prefixes: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`. Example:
`feat: real Sentinel-1 loader for M1`.

## Opening a PR

```bash
git push -u origin feature/<your-branch>
```
Then open a PR on GitHub into `main`. Fill in the PR template — the key
question it asks is whether your output still matches the contract shape
for your stage. If you changed the contract itself, say so explicitly and
tag the team, since it affects everyone downstream.

## Testing your module in isolation

Every module has a `__main__` block, so you can run and sanity-check your
piece alone against the demo data without the rest of the team's code
being finished:
```bash
python3 -m backend.<your_module_path> data/runtime demo_scene_01
```
Check the printed/written JSON against the shape in
`docs/API_CONTRACT.md` before opening a PR.

## Code style

- Python 3.10+, type hints on function signatures.
- Keep `backend/common/geo.py` as the *only* place that does lon/lat
  pixel math or great-circle distance — import from it rather than
  re-deriving formulas, so every module agrees on the same geometry.
- Docstring at the top of every module: what it does, and how to run it
  standalone.
