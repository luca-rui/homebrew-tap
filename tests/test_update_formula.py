#!/usr/bin/env python3
"""Tests for scripts/update_formula.py. No network: PyPI is a dict here.

    python3 -I tests/test_update_formula.py

Standard library only.
"""
import hashlib
import importlib.util
import io
import os
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "update_formula", os.path.join(HERE, "..", "scripts", "update_formula.py"))
uf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uf)


def stops(call, *args):
    """The message a call stops the script with, None when it returns."""
    try:
        call(*args)
    except SystemExit as e:
        return str(e.code)
    return None


def files(*names, yanked=False):
    return [{"filename": n, "url": f"https://files.example/{n}", "yanked": yanked,
             "digests": {"sha256": hashlib.sha256(n.encode()).hexdigest()}} for n in names]


def project(name, releases, requires=()):
    """PyPI's answer for a project: releases is {version: files}, oldest first."""
    newest = list(releases)[-1]
    return {"info": {"version": newest, "requires_dist": list(requires)},
            "releases": releases, "urls": releases[newest]}


def publish(pypi, name, version, new):
    """A new newest release of a project."""
    pypi[name]["releases"][version] = new
    pypi[name]["info"]["version"] = version
    pypi[name]["urls"] = new


def both(stem):
    """A release with one wheel per architecture."""
    return files(f"{stem}-cp314-cp314-macosx_11_0_arm64.whl",
                 f"{stem}-cp314-cp314-macosx_10_15_x86_64.whl", f"{stem}.tar.gz")


def index():
    """A small PyPI with everything the script asks for."""
    pyobjc = lambda n: {"13.0": files(f"{n}-13.0-cp314-cp314-macosx_10_15_universal2.whl")}
    return {
        "rga-ocr": project("rga-ocr", {"0.2.4": files("rga_ocr-0.2.4-py3-none-any.whl")}, [
            "platformdirs>=4", "pillow>=10.1", "pi-heif>=0.22", "pypdfium2>=4.30",
            "pyobjc-framework-Vision>=10; sys_platform == 'darwin' and extra == 'vision'",
            "pyobjc-framework-Quartz>=10; sys_platform == 'darwin' and extra == 'vision'",
            "winrt-runtime>=2.0.1; sys_platform == 'win32' and extra == 'winocr'"]),
        "pi-heif": project("pi-heif", {"1.3.0": both("pi_heif-1.3.0"), "1.4.0": both("pi_heif-1.4.0")},
                           ["pillow>=11.1.0", "pytest; extra == 'tests'"]),
        "pillow": project("pillow", {"11.0.0": both("pillow-11.0.0"), "12.0.0": both("pillow-12.0.0"),
                                     "13.0.0": both("pillow-13.0.0")}),
        "platformdirs": project("platformdirs", {"4.9.6": files("platformdirs-4.9.6-py3-none-any.whl"),
                                                 "4.14.7": files("platformdirs-4.14.7-py3-none-any.whl")}),
        "pyobjc-core": project("pyobjc-core", pyobjc("pyobjc_core")),
        "pyobjc-framework-Cocoa": project("pyobjc-framework-Cocoa", pyobjc("pyobjc_framework_cocoa"),
                                          ["pyobjc-core>=13.0"]),
        "pyobjc-framework-CoreML": project("pyobjc-framework-CoreML", pyobjc("pyobjc_framework_coreml"),
                                           ["pyobjc-core>=13.0"]),
        "pyobjc-framework-Quartz": project("pyobjc-framework-Quartz", pyobjc("pyobjc_framework_quartz"),
                                           ["pyobjc-core>=13.0"]),
        "pyobjc-framework-Vision": project("pyobjc-framework-Vision", pyobjc("pyobjc_framework_vision"),
                                           ["pyobjc-core>=13.0"]),
        "pypdfium2": project("pypdfium2", {"5.15.2": files("pypdfium2-5.15.2-py3-none-macosx_13_0_arm64.whl",
                                                           "pypdfium2-5.15.2-py3-none-macosx_13_0_x86_64.whl")}),
    }


class Tap:
    """The script with a PyPI of our own and a formula in a temp directory."""

    def __init__(self, pypi):
        self.pypi = pypi
        self.asked = []
        self.dir = tempfile.TemporaryDirectory()
        uf.FORMULA = os.path.join(self.dir.name, "rga-ocr.rb")
        uf.pypi = self.answer

    def answer(self, name):
        self.asked.append(name)
        return self.pypi[name]

    def run(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = uf.main(list(argv))
        return code, out.getvalue().splitlines()

    def formula(self):
        with open(uf.FORMULA, encoding="utf-8") as f:
            return f.read()

    def edit(self, old, new):
        text = self.formula()
        assert old in text
        with open(uf.FORMULA, "w", encoding="utf-8") as f:
            f.write(text.replace(old, new))


def test_release_order():
    key = uf.release_key
    assert key("13.0") == key("13.0.0") == key("13")
    assert key("9.1b1") is None and key("2.0rc1") is None and key("1.0.dev3") is None
    assert key("4.14.7") > key("4.9.6") > key("4.9")
    assert key("1.0.post1") > key("1.0") and key("1.0.1") > key("1.0.post1")


def test_specifiers():
    ok = uf.satisfies
    assert ok("13.0.0", "") and ok("13.0.0", ">=10.1") and not ok("10.0", ">=10.1")
    assert ok("11.1", ">=11.1.0") and ok("4.0", ">=4") and not ok("3.9", ">=4")
    assert ok("11.2", ">=10.1,<12") and not ok("12.0", ">=10.1, <12")
    assert ok("12.0", "<=12") and not ok("12.0.1", "<=12")
    assert ok("1.2.9", "==1.2.*") and not ok("1.3.0", "==1.2.*") and ok("1.3", "!=1.2.*")
    assert ok("1.2", "==1.2.0") and not ok("1.2.1", "==1.2") and ok("1.2.1", "!=1.2")
    assert ok("1.4.5", "~=1.4.2") and not ok("1.5.0", "~=1.4.2") and not ok("1.4.1", "~=1.4.2")
    assert ok("2.9", "~=2.2") and not ok("3.0", "~=2.2")
    assert ok("1.1", ">1.0") and not ok("1.0", ">1.0") and not ok("1.0.post1", ">1.0")
    assert ok("1.0.post2", ">1.0.post1")
    # What it cannot read stops the script instead of passing.
    for bad in (">=1.0rc1", "===1.0", ">=1.*", "~=1", "@ https://x/y.whl", "~=1.0.post1"):
        assert "cannot read" in stops(ok, "1.0", bad), bad


def test_requirements():
    meta = {"info": {"requires_dist": [
        "pillow>=10.1", "Pi_Heif (>=0.22)", "platformdirs", "pillow<14",
        "pyobjc-framework-Vision[x]>=10; sys_platform == 'darwin' and extra == 'vision'",
        "winrt-runtime>=2.0.1; extra == 'winocr'"]}}
    assert uf.requirements(meta, "vision") == {
        "pillow": ">=10.1,<14", "pi-heif": ">=0.22", "platformdirs": "", "pyobjc-framework-vision": ">=10"}
    assert "pyobjc-framework-vision" not in uf.requirements(meta)
    assert "cannot read" in stops(uf.requirements, {"info": {"requires_dist": ["x @ https://y/z.whl"]}})
    assert "requires winrt-runtime" in stops(uf.check_closure, uf.requirements(meta, "winocr"))


def test_pick_takes_the_newest():
    version, found, note = uf.pick("pillow", index()["pillow"], ">=10.1")
    assert version == "13.0.0" and note is None
    assert found["arm64"][0].endswith("pillow-13.0.0-cp314-cp314-macosx_11_0_arm64.whl")
    version, found, note = uf.pick("platformdirs", index()["platformdirs"], ">=4")
    assert version == "4.14.7" and note is None and set(found) == {"any"}


def test_pick_falls_back():
    pillow = index()["pillow"]
    # The newest release has no Intel wheel yet, and a pre-release is no candidate.
    pillow["releases"]["13.0.0"] = files("pillow-13.0.0-cp314-cp314-macosx_11_0_arm64.whl",
                                         "pillow-13.0.0-cp313-cp313-macosx_10_15_x86_64.whl",
                                         "pillow-13.0.0-cp314-cp314-win_amd64.whl", "pillow-13.0.0.tar.gz")
    pillow["releases"]["13.1.0b1"] = both("pillow-13.1.0b1")
    version, found, note = uf.pick("pillow", pillow, ">=10.1")
    assert version == "12.0.0"
    assert found["x86_64"][0].endswith("pillow-12.0.0-cp314-cp314-macosx_10_15_x86_64.whl")
    assert note == ("pillow 12.0.0: not the newest release; "
                    "13.0.0 has no macOS wheel for cp314 on both architectures"), note

    # A yanked release and one above rga-ocr's cap are passed over, with the reason.
    pillow = index()["pillow"]
    pillow["releases"]["13.0.0"] = both("pillow-13.0.0")
    for f in pillow["releases"]["13.0.0"]:
        f["yanked"] = True
    version, _, note = uf.pick("pillow", pillow, ">=10.1,<12")
    assert version == "11.0.0"
    assert note == ("pillow 11.0.0: not the newest release; 13.0.0 has no files, or only yanked ones; "
                    "12.0.0 is not >=10.1,<12, which rga-ocr requires"), note

    # Nothing left: the script stops and says what it looked at.
    said = stops(uf.pick, "pillow", pillow, ">=14")
    assert said.startswith("pillow: no release to pin; 13.0.0 has no files"), said
    # The floor is not undercut to find wheels.
    pillow = index()["pillow"]
    pillow["releases"]["13.0.0"] = files("pillow-13.0.0.tar.gz")
    pillow["releases"]["12.0.0"] = files("pillow-12.0.0.tar.gz")
    assert "11.0.0 is not >=11.1" in stops(uf.pick, "pillow", pillow, ">=11.1")


def test_fallback_reaches_the_formula_and_the_output():
    pypi = index()
    pypi["pillow"]["releases"]["13.0.0"] = files("pillow-13.0.0.tar.gz")
    pypi["pillow/12.0.0"] = project("pillow", {"12.0.0": both("pillow-12.0.0")})
    tap = Tap(pypi)
    code, lines = tap.run()
    assert code == 0 and lines == [
        "pillow 12.0.0: not the newest release; 13.0.0 has no macOS wheel for cp314 on both architectures",
        "rga-ocr 0.2.4: formula written"], lines
    assert "pillow-12.0.0-cp314" in tap.formula() and "pillow-13" not in tap.formula()
    # pillow 12.0.0 is not PyPI's newest, so the requirements of that release were asked for.
    assert "pillow/12.0.0" in tap.asked
    assert tap.run("--check")[0] == 0


def test_picks_must_fit_each_other():
    pypi = index()
    # pi-heif 1.4.0 wants pillow>=11.1, and only pillow 11.0.0 has wheels.
    pypi["pillow"]["releases"]["13.0.0"] = files("pillow-13.0.0.tar.gz")
    pypi["pillow"]["releases"]["12.0.0"] = files("pillow-12.0.0.tar.gz")
    tap = Tap(pypi)
    said = stops(tap.run)
    assert said == "pi-heif 1.4.0 requires pillow>=11.1.0, but the release to pin is pillow 11.0.0", said
    assert not os.path.exists(uf.FORMULA)


def test_revision():
    pypi = index()
    tap = Tap(pypi)
    assert tap.run("--check") == (1, ["rga-ocr 0.2.4: formula would change"])
    assert tap.run() == (0, ["rga-ocr 0.2.4: formula written"])
    first = tap.formula()
    assert "revision" not in first
    assert tap.run() == (0, ["rga-ocr 0.2.4: formula is up to date"])
    assert tap.run("--check")[0] == 0 and tap.formula() == first

    # A dependency moves, rga-ocr does not: revision 1, directly under license.
    publish(pypi, "platformdirs", "4.15.0", files("platformdirs-4.15.0-py3-none-any.whl"))
    assert tap.run("--new-release") == (0, ["rga-ocr 0.2.4: the formula has this release"])
    assert tap.formula() == first
    assert tap.run("--check") == (1, ["rga-ocr 0.2.4_1: formula would change"])
    assert tap.run() == (0, ["rga-ocr 0.2.4_1: formula written"])
    assert '  license "MIT"\n  revision 1\n\n  depends_on :macos\n' in tap.formula()
    assert "platformdirs-4.15.0" in tap.formula()
    second = tap.formula()
    # A second run adds nothing.
    assert tap.run() == (0, ["rga-ocr 0.2.4_1: formula is up to date"]) and tap.formula() == second

    # The next dependency release is one more.
    publish(pypi, "pillow", "13.0.1", both("pillow-13.0.1"))
    assert tap.run() == (0, ["rga-ocr 0.2.4_2: formula written"])
    assert "  revision 2\n" in tap.formula() and "revision 1" not in tap.formula()

    # A change that touches no pinned file is rewritten without a higher revision.
    tap.edit("# Keeps the install name", "# Keeps the name")
    assert tap.run() == (0, ["rga-ocr 0.2.4_2: formula written"])
    assert "  revision 2\n" in tap.formula() and "# Keeps the install name" in tap.formula()

    # A new rga-ocr drops the line, also when dependencies move with it.
    publish(pypi, "rga-ocr", "0.2.5", files("rga_ocr-0.2.5-py3-none-any.whl"))
    publish(pypi, "pillow", "13.0.2", both("pillow-13.0.2"))
    assert tap.run("--new-release") == (0, ["rga-ocr 0.2.5: formula written"])
    assert "revision" not in tap.formula() and "rga_ocr-0.2.5-py3" in tap.formula()
    assert "pillow-13.0.2" in tap.formula()


def test_formula_fields():
    tap = Tap(index())
    tap.run()
    text = tap.formula()
    assert uf.formula_version(text) == "0.2.4" and uf.formula_revision(text) == 0
    assert uf.formula_version("") is None and uf.formula_revision("") == 0
    # 1 file for rga-ocr, 3 packages twice, 6 packages once; url and sha256 each.
    assert len(uf.pins(text)) == 2 * (1 + 3 * 2 + 6)


if __name__ == "__main__":
    tests = [(name, call) for name, call in sorted(globals().items()) if name.startswith("test_")]
    for name, call in tests:
        call()
        print(f"ok  {name}")
    print(f"{len(tests)} tests passed")
