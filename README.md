# About

`changelog` is a minimal [sphinx](https://www.sphinx-doc.org/en/master/) extension to easily add changelogs of Github repositories to your documentations.

# Install

With `pip`:
```bash
/path/to/venv/bin/pip install git+https://github.com/ximenesyuri/changelog
```

With [py](https://github.com/ximenesyuri/py):
```bash
py install ximenesyuri/changelog --from github
```

# Usage

1. In your `conf.py` file, include the `changelog` package (be sure to also had included `myst_parser`):
```python
extensions = ['myst_parser', 'changelog']
```
2. In a `.md` file add a `changelog` code block:
```markdown
```{changelog}
:repo: github.com/{owner}/{repo}
:kind: tag/release
:title: true/false
:desc: true/false
:date: true/false
:commits: true/false
```
```
