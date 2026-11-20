#!/usr/bin/env python3
"""Write Formula/rga-ocr.rb from what PyPI serves.

The formula installs wheels, not sdists: pypdfium2, pi-heif and pyobjc
are no reasonable source builds inside a formula. Every wheel is pinned
by URL and sha256. This script looks up the newest release of rga-ocr
and of each dependency and rewrites the formula.

    update_formula.py                 rewrite the formula
    update_formula.py --new-release   rewrite it only when PyPI has another
                                      rga-ocr than the formula; dependency
                                      releases alone change nothing
    update_formula.py --check         exit 1 when the formula would change

A dependency is pinned at its newest final release that rga-ocr's own
requirements allow and that has the wheels the formula needs. When that
is not the newest release, the output says which one was passed over and
why.

When the pinned wheels change and rga-ocr itself does not, the formula
gets a `revision` one higher than before: without it `brew upgrade` sees
the same version and leaves the installed copy alone. A new rga-ocr
drops the line again.

Standard library only.
"""
import gzip
import json
import os
import re
import sys
import time
import urllib.request

FORMULA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Formula", "rga-ocr.rb")
PACKAGE = "rga-ocr"
EXTRA = "vision"
# The interpreter the formula depends on, and its wheel tag. Raise both
# together, once every dependency below ships wheels for the new one.
PYTHON_FORMULA = "python@3.14"
PYTHON_TAG = "cp314"
# rga-ocr[vision] on macOS with everything it pulls in. check_closure()
# fails when rga-ocr starts to require something that is not listed.
DEPENDENCIES = [
    "pi-heif",
    "pillow",
    "platformdirs",
    "pyobjc-core",
    "pyobjc-framework-Cocoa",
    "pyobjc-framework-CoreML",
    "pyobjc-framework-Quartz",
    "pyobjc-framework-Vision",
    "pypdfium2",
]

TEMPLATE = '''class RgaOcr < Formula
  include Language::Python::Virtualenv

  desc "Search PDFs, images and Office files with ripgrep-all and local OCR"
  homepage "https://github.com/luca-rui/rga-ocr"
  url "{url}"
  sha256 "{sha256}"
  license "MIT"
{revision}
  depends_on :macos
  depends_on "pandoc"
  depends_on "{python_formula}"
  depends_on "ripgrep"
  depends_on "ripgrep-all"

  on_arm do
{arm}  end

  on_intel do
{intel}  end

  # Keeps the install name that `install` gives pdfium on Intel.
  preserve_rpath

{common}
  def install
    # Every dependency is a resource, so the environment does not need to
    # see the packages of Homebrew's Python.
    venv = virtualenv_create(libexec, "{python_command}", system_site_packages: false)
    resources.each do |r|
      r.stage do
        venv.pip_install Pathname.pwd/r.downloader.basename
      end
    end
    venv.pip_install_and_link buildpath/File.basename(stable.url)

    # The Intel build of pdfium has no room in its header for the long
    # install name Homebrew would write. pypdfium2 loads the library by
    # path, so a short name that Homebrew leaves alone does the job.
    return unless Hardware::CPU.intel?

    pdfium = venv.site_packages/"pypdfium2_raw/libpdfium.dylib"
    MachO::Tools.change_dylib_id(pdfium, "@rpath/libpdfium.dylib")
  end

  test do
    assert_match version.to_s, shell_output("#{{bin}}/rga-ocr --version")
    assert_match(/vision\\s+yes/, shell_output("#{{bin}}/rga-ocr --engines"))
  end
end
'''


def norm(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def pypi(name):
    url = f"https://pypi.org/pypi/{name}/json"
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return json.loads(body)
        except Exception as e:      # PyPI cuts a large answer short now and then
            last = e
            time.sleep(2 * (attempt + 1))
    raise SystemExit(f"{url}: {last}")


def wheels(files):
    """{'any' | 'arm64' | 'x86_64': (url, sha256)} for the pinned Python."""
    found = {}
    for f in files:
        name = f["filename"]
        if not name.endswith(".whl"):
            continue
        python, abi, platform = name[:-4].split("-")[-3:]
        if not (python == PYTHON_TAG or python.startswith("py3")):
            continue
        if abi not in (PYTHON_TAG, "none", "abi3"):
            continue
        entry = (f["url"], f["digests"]["sha256"])
        if platform == "any" or "universal2" in platform:
            found["any"] = entry
        elif platform.startswith("macosx") and platform.endswith("arm64"):
            found["arm64"] = entry
        elif platform.startswith("macosx") and platform.endswith("x86_64"):
            found["x86_64"] = entry
    return found


def release_key(version):
    """Sort key of a final release; None for a pre-release or a dev build."""
    m = re.fullmatch(r"(\d+(?:\.\d+)*)(?:\.post(\d+))?", version)
    if not m:
        return None
    release = [int(n) for n in m.group(1).split(".")]
    while len(release) > 1 and release[-1] == 0:      # 13.0 is 13
        release.pop()
    return tuple(release), int(m.group(2)) if m.group(2) else -1


def satisfies(version, specifier):
    """Whether a final release meets a specifier such as '>=10.1,<12'.

    A clause this does not understand stops the script: skipping it would
    drop a constraint without a word.
    """
    key = release_key(version)
    for clause in filter(None, (c.strip() for c in specifier.split(","))):
        m = re.fullmatch(r"(~=|==|!=|<=|>=|<|>)\s*(\d+(?:\.\d+)*)(\.post\d+)?(\.\*)?", clause)
        if not m:
            raise SystemExit(f"cannot read the version specifier {specifier!r}")
        op, number, post, wildcard = m.groups()
        parts = tuple(int(n) for n in number.split("."))
        if wildcard or op == "~=":
            # ==1.2.* and ~=1.2.3 name a series: 1.2.anything.
            if post or (wildcard and op not in ("==", "!=")) or (op == "~=" and len(parts) < 2):
                raise SystemExit(f"cannot read the version specifier {specifier!r}")
            series = parts if wildcard else parts[:-1]
            inside = (key[0] + (0,) * len(series))[:len(series)] == series
            if op == "!=":
                ok = not inside
            elif op == "==":
                ok = inside
            else:
                ok = inside and key >= release_key(number)
        else:
            bound = release_key(number + (post or ""))
            if op == "==":
                ok = key == bound
            elif op == "!=":
                ok = key != bound
            elif op == ">=":
                ok = key >= bound
            elif op == "<=":
                ok = key <= bound
            elif op == "<":
                ok = key < bound
            elif post:
                ok = key > bound
            else:
                ok = key[0] > bound[0]      # >1.0 does not take 1.0.post1
        if not ok:
            return False
    return True


def requirements(meta, extra=None):
    """{name: specifier} of what a release requires, core and the one extra."""
    found = {}
    for req in meta["info"].get("requires_dist") or []:
        spec, _, marker = req.partition(";")
        if "extra ==" in marker and not (extra and re.search(rf"extra == ['\"]{extra}['\"]", marker)):
            continue
        m = re.fullmatch(r"\s*([A-Za-z0-9._-]+)\s*(?:\[[^\]]*\])?\s*\(?([^()@]*)\)?\s*", spec)
        if not m:
            raise SystemExit(f"cannot read the requirement {req!r}")
        found.setdefault(norm(m.group(1)), []).append(m.group(2).strip())
    return {name: ",".join(filter(None, specs)) for name, specs in found.items()}


def check_closure(required):
    """rga-ocr's own requirements, core and the extra, must be listed."""
    missing = sorted(set(required) - {norm(d) for d in DEPENDENCIES})
    if missing:
        raise SystemExit(f"{PACKAGE} requires {', '.join(missing)}: add to DEPENDENCIES "
                         "together with whatever it pulls in")


def pick(name, meta, specifier):
    """(version, wheels, note) of the release to pin.

    That is the newest final release which rga-ocr's requirement allows
    and which has a wheel for every Mac. The note is None when this is
    the newest release, and says what was passed over when it is not.
    """
    passed = []
    final = sorted(((release_key(v), v) for v in meta["releases"] if release_key(v)), reverse=True)
    for _, version in final:
        files = [f for f in meta["releases"][version] if not f.get("yanked")]
        if not files:
            why = "has no files, or only yanked ones"
        elif not satisfies(version, specifier):
            why = f"is not {specifier}, which {PACKAGE} requires"
        else:
            found = wheels(files)
            if "any" in found or ("arm64" in found and "x86_64" in found):
                note = None
                if passed:
                    more = f" (and {len(passed) - 3} more)" if len(passed) > 3 else ""
                    note = f"{name} {version}: not the newest release; {'; '.join(passed[:3])}{more}"
                return version, found, note
            why = f"has no macOS wheel for {PYTHON_TAG} on both architectures"
        passed.append(f"{version} {why}")
    more = f" (and {len(passed) - 3} more)" if len(passed) > 3 else ""
    raise SystemExit(f"{name}: no release to pin; {'; '.join(passed[:3]) or 'PyPI lists no final release'}{more}")


def check_set(picked, newest):
    """What the pinned releases require of each other must hold.

    Each release is picked on its own, so an older pick of one package can
    fall below what another one asks for. picked is {name: version},
    newest is {name: PyPI's answer for the project}.
    """
    versions = {norm(name): version for name, version in picked.items()}
    for name, version in picked.items():
        meta = newest[name]
        if meta["info"]["version"] != version:
            meta = pypi(f"{name}/{version}")
        for other, specifier in requirements(meta).items():
            if other in versions and not satisfies(versions[other], specifier):
                raise SystemExit(f"{name} {version} requires {other}{specifier}, "
                                 f"but the release to pin is {other} {versions[other]}")


def resource(name, entry, indent):
    pad = " " * indent
    return (f'{pad}resource "{name}" do\n{pad}  url "{entry[0]}"\n'
            f'{pad}  sha256 "{entry[1]}"\n{pad}end\n')


def formula_version(text):
    """The rga-ocr release a formula installs, None when there is none."""
    m = re.search(r'^  url ".*/rga_ocr-([^-/"]+)-[^/"]*"$', text, re.M)
    return m.group(1) if m else None


def formula_revision(text):
    m = re.search(r"^  revision (\d+)$", text, re.M)
    return int(m.group(1)) if m else 0


def pins(text):
    """Every pinned file of a formula, in order."""
    return re.findall(r'^ +(?:url|sha256) "([^"]*)"$', text, re.M)


def render(meta, old=""):
    """(version, revision, formula, notes) for PyPI's rga-ocr, given the formula so far."""
    version = meta["info"]["version"]
    required = requirements(meta, EXTRA)
    check_closure(required)
    main = wheels(meta["urls"]).get("any")
    if not main:
        raise SystemExit(f"{PACKAGE} {version}: no py3-none-any wheel")
    common, arm, intel, notes = [], [], [], []
    picked, newest = {}, {}
    for name in DEPENDENCIES:
        newest[name] = pypi(name)
        picked[name], w, note = pick(name, newest[name], required.get(norm(name), ""))
        if note:
            notes.append(note)
        if "any" in w:
            common.append(resource(name, w["any"], 2))
        else:
            arm.append(resource(name, w["arm64"], 4))
            intel.append(resource(name, w["x86_64"], 4))
    check_set(picked, newest)

    def formula(revision):
        return TEMPLATE.format(url=main[0], sha256=main[1], python_formula=PYTHON_FORMULA,
                               python_command=PYTHON_FORMULA.replace("@", ""),
                               revision=f"  revision {revision}\n" if revision else "",
                               arm="\n".join(arm), intel="\n".join(intel), common="\n".join(common))

    # Same rga-ocr with other wheels is one revision up, so that an installed
    # copy is upgraded. Anything else that differs, a comment or the install
    # steps, is no reason for it. Another rga-ocr starts without a revision.
    revision = 0
    if formula_version(old) == version:
        revision = formula_revision(old)
        if pins(formula(revision)) != pins(old):
            revision += 1
    return version, revision, formula(revision), notes


def main(argv):
    old = ""
    if os.path.exists(FORMULA):
        with open(FORMULA, encoding="utf-8") as f:
            old = f.read()
    meta = pypi(PACKAGE)
    if "--new-release" in argv:
        release = meta["info"]["version"]
        if formula_version(old) == release:
            print(f"{PACKAGE} {release}: the formula has this release")
            return 0
    version, revision, text, notes = render(meta, old)
    for note in notes:
        print(note)
    # Homebrew's own spelling of a revision: 0.2.4_1.
    label = f"{PACKAGE} {version}_{revision}" if revision else f"{PACKAGE} {version}"
    if text == old:
        print(f"{label}: formula is up to date")
        return 0
    if "--check" in argv:
        print(f"{label}: formula would change")
        return 1
    with open(FORMULA, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"{label}: formula written")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
