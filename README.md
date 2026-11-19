# luca-rui/homebrew-tap

Homebrew formulae for my tools.

## rga-ocr

[rga-ocr](https://github.com/luca-rui/rga-ocr) searches PDFs, images and
Office files with ripgrep-all and local OCR.

```
brew install luca-rui/tap/rga-ocr
rga-ocr setup --apply
```

The second command wires the OCR adapters into ripgrep-all. It is needed
once, not after every upgrade.

Upgrade and removal:

```
brew upgrade rga-ocr
brew uninstall rga-ocr
```

What the formula does:

- It installs `ripgrep`, `ripgrep-all` and `pandoc` as dependencies.
- It is macOS only and carries one OCR engine, Apple Vision. For
  Tesseract, RapidOCR or Windows OCR, use the
  [PyPI install](https://github.com/luca-rui/rga-ocr#install) instead.
- It runs on Homebrew's `python@3.14` in a private environment. The
  Python dependencies are installed from the wheels on PyPI, each pinned
  by URL and sha256, because several of them are no reasonable source
  builds. There are no bottles; the install only unpacks wheels and takes
  seconds.

## Maintenance

`scripts/update_formula.py` writes `Formula/rga-ocr.rb` from the newest
releases on PyPI. The `bump` workflow runs it daily and opens a pull
request when PyPI has a new rga-ocr; the dependencies move along in the
same pull request. A manual run with `dependencies` ticked takes new
dependency releases without a new rga-ocr. The `test` workflow installs,
tests and audits the formula on macOS for every pull request.

GitHub switches a scheduled workflow off after 60 days without activity
in the repository. If a release does not show up here, enable `bump`
again under Actions and run it by hand.

Moving to a newer Python is a change of `PYTHON_FORMULA` and `PYTHON_TAG`
in the script, once every dependency ships wheels for it.
