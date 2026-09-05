# Publishing a release

The version is the git tag. `pyproject.toml` declares `dynamic = ["version"]` and
setuptools-scm reads it from the repository, so there is no number to bump in any
file — tagging *is* the version bump.

```bash
git switch main && git pull            # release from main, up to date
git status --porcelain                 # must print nothing: see below
pytest                                 # and CI green on the commit you are tagging

git tag 1.2.0 && git push origin 1.2.0 # the tag IS the version

rm -rf dist/
python -m build
python -m twine check dist/*
python -m twine upload --repository pypi dist/*
```

Three things that will bite you, in the order they will:

* **A dirty tree cannot be published.** setuptools-scm appends a local segment to
  the version (`1.2.0.dev0+d20260905`), and PyPI refuses any version carrying one.
  The upload fails after the build, not before.
* **Tag before building.** Build first and you get `1.1.1.dev4+g1782fb9`, the *next*
  version in development, not the one you meant.
* **Empty `dist/` first.** `twine upload dist/*` sends everything in there, and
  re-sending an already published file is an error that aborts the whole upload.

Check what landed with `pip index versions custom-profiler`. The PyPI badge in the
README follows on its own.

A release is never undone: a version number on PyPI cannot be reused, even after
deleting the file. If you get it wrong, publish the next patch.
