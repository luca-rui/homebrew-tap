# luca-rui/homebrew-tap

Homebrew formulae for my tools.

## rga-ocr

[rga-ocr](https://github.com/luca-rui/rga-ocr) searches PDFs, images and
Office files with ripgrep-all and local OCR.

```
brew install luca-rui/tap/rga-ocr
```

That is all: `rga-ocr <query> <path>` searches right away. Only plain
`rga` needs `rga-ocr setup --apply` once, which writes the OCR adapters
into ripgrep-all's own config.

Upgrade:

```
brew upgrade rga-ocr
```

Removal:

```
rga-ocr setup --remove       # only after `setup --apply`
rga-ocr --clear-cache all
brew uninstall rga-ocr
```

`brew uninstall` takes the program away and nothing else. `setup --remove`
takes the OCR adapters out of ripgrep-all's config, which would otherwise
point at a Python that is gone, and lists what else rga-ocr left on disk.
`--clear-cache all` deletes the OCR cache. Both need rga-ocr, so run them
first. `brew autoremove` afterwards removes the dependencies that nothing
else uses.

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

`scripts/update_formula.py` writes `Formula/rga-ocr.rb` from PyPI. Each
dependency is pinned at its newest release that rga-ocr's requirements
allow and that has wheels for both Macs. When that is not the newest
release, the script says which one it passed over and why.

The `bump` workflow runs the script and opens a pull request from the
branch `bump/formula` when the formula changes:

- daily for a new rga-ocr; the dependencies move along in the same pull
  request,
- on Mondays for new dependency releases without a new rga-ocr. A manual
  run with `dependencies` ticked does the same.

A formula that changes without a new rga-ocr gets a `revision`, so that
`brew upgrade` installs the new wheels. The next rga-ocr drops it again.

The `test` workflow installs, tests and audits the formula on macOS for
every pull request and every push to `main`, and once a week on `main`,
because the formula's Homebrew dependencies are not pinned. It also runs
the tests of the script, `python3 -I tests/test_update_formula.py`.

`test` reports its result as the commit status `formula-tests`. The pull
request run of a `bump` pull request waits for an approval by hand,
because the pull request was opened with the workflow's own token. `bump`
therefore starts `test` on its branch itself, and the status of that run
counts for the pull request. A pull request from a fork gets no status
from its own run: push its head commit to a branch here and run `test`
on that branch.

GitHub switches a scheduled workflow off after 60 days without activity
in the repository. If a release does not show up here, enable `bump`
and `test` again under Actions and run `bump` by hand.

Moving to a newer Python is a change of `PYTHON_FORMULA` and `PYTHON_TAG`
in the script, once every dependency ships wheels for it.
