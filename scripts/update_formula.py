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

  depends_on :macos
  depends_on "pandoc"
  depends_on "{python_formula}"
  depends_on "ripgrep"
  depends_on "ripgrep-all"

  on_arm do
{arm}  end

  on_intel do
{intel}  end

{common}
  def install
    venv = virtualenv_create(libexec, "{python_command}")
    resources.each do |r|
      r.stage do
        venv.pip_install Pathname.pwd/r.downloader.basename
      end
    end
    venv.pip_install_and_link buildpath/File.basename(stable.url)
  end

  def caveats
    <<~EOS
      Wire the OCR adapters into ripgrep-all once:
        rga-ocr setup --apply
    EOS
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


def wheels(meta):
    """{'any' | 'arm64' | 'x86_64': (url, sha256)} for the pinned Python."""
    found = {}
    for f in meta["urls"]:
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


def check_closure(meta):
    """rga-ocr's own requirements, core and the extra, must be listed."""
    known = {norm(d) for d in DEPENDENCIES}
    missing = []
    for req in meta["info"].get("requires_dist") or []:
        spec, _, marker = req.partition(";")
        if "extra ==" in marker and not re.search(rf"extra == ['\"]{EXTRA}['\"]", marker):
            continue
        name = norm(re.match(r"[A-Za-z0-9._-]+", spec.strip()).group(0))
        if name not in known:
            missing.append(name)
    if missing:
        raise SystemExit(f"{PACKAGE} requires {', '.join(missing)}: add to DEPENDENCIES "
                         "together with whatever it pulls in")


def resource(name, entry, indent):
    pad = " " * indent
    return (f'{pad}resource "{name}" do\n{pad}  url "{entry[0]}"\n'
            f'{pad}  sha256 "{entry[1]}"\n{pad}end\n')


def render(meta):
    check_closure(meta)
    main = wheels(meta).get("any")
    if not main:
        raise SystemExit(f"{PACKAGE} {meta['info']['version']}: no py3-none-any wheel")
    common, arm, intel = [], [], []
    for name in DEPENDENCIES:
        dep = pypi(name)
        w = wheels(dep)
        version = dep["info"]["version"]
        if "any" in w:
            common.append(resource(name, w["any"], 2))
        elif "arm64" in w and "x86_64" in w:
            arm.append(resource(name, w["arm64"], 4))
            intel.append(resource(name, w["x86_64"], 4))
        else:
            raise SystemExit(f"{name} {version}: no macOS wheel for {PYTHON_TAG} on both architectures")
    text = TEMPLATE.format(url=main[0], sha256=main[1], python_formula=PYTHON_FORMULA,
                           python_command=PYTHON_FORMULA.replace("@", ""),
                           arm="\n".join(arm), intel="\n".join(intel), common="\n".join(common))
    return meta["info"]["version"], text


def main(argv):
    old = ""
    if os.path.exists(FORMULA):
        with open(FORMULA, encoding="utf-8") as f:
            old = f.read()
    meta = pypi(PACKAGE)
    if "--new-release" in argv:
        release = meta["info"]["version"]
        if re.search(rf'^  url ".*/rga_ocr-{re.escape(release)}-[^/"]*"$', old, re.M):
            print(f"{PACKAGE} {release}: the formula has this release")
            return 0
    version, text = render(meta)
    if text == old:
        print(f"{PACKAGE} {version}: formula is up to date")
        return 0
    if "--check" in argv:
        print(f"{PACKAGE} {version}: formula would change")
        return 1
    with open(FORMULA, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"{PACKAGE} {version}: formula written")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
