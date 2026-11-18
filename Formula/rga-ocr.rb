class RgaOcr < Formula
  include Language::Python::Virtualenv

  desc "Search PDFs, images and Office files with ripgrep-all and local OCR"
  homepage "https://github.com/luca-rui/rga-ocr"
  url "https://files.pythonhosted.org/packages/7f/6d/86b22abfb988152d04526d6b55f88447ffa75407093bdde169284ed0033c/rga_ocr-0.2.1-py3-none-any.whl"
  sha256 "05517761471dc5d1d3a9b7b4e422fce0bc7447250a1c22c94346d26c5f83c643"
  license "MIT"

  depends_on :macos
  depends_on "pandoc"
  depends_on "python@3.14"
  depends_on "ripgrep"
  depends_on "ripgrep-all"

  on_arm do
    resource "pi-heif" do
      url "https://files.pythonhosted.org/packages/f5/4a/49ca58461582c03984957d87066ff3f3106e1e97b4893442ca3f2e623e77/pi_heif-1.4.0-cp314-cp314-macosx_11_0_arm64.whl"
      sha256 "3d5396f500e70de167307e0cabcc2b3895d2e623ad4243811f44d578b55c9e1c"
    end

    resource "pillow" do
      url "https://files.pythonhosted.org/packages/b5/f4/0bf6f1ac9ba7ee2ffe9914aeb410a1035a0c1a3c42f122388d7fc950bc4b/pillow-13.0.0-cp314-cp314-macosx_11_0_arm64.whl"
      sha256 "d9b0a2bee3f3e03e9f29057aedb807dbf1e1d96ee1b9d0f422d9db6c8583271d"
    end

    resource "pypdfium2" do
      url "https://files.pythonhosted.org/packages/e7/bb/bf88a781a53c905022b25b2d1fb742c908f86b8076403471f626cc41a508/pypdfium2-5.15.2-py3-none-macosx_13_0_arm64.whl"
      sha256 "e71fe832e94421ac3c28d6a6ed4a9e61f22417089652d339f391c4ffc2a44c35"
    end
  end

  on_intel do
    resource "pi-heif" do
      url "https://files.pythonhosted.org/packages/35/79/eb28acbc84d7a62121c90d97b4e5672f221d4cc1e856f81ac590d40a1080/pi_heif-1.4.0-cp314-cp314-macosx_10_15_x86_64.whl"
      sha256 "13eceb34f2bfe06b1e59296e958a67cbe864adb10d30e825890e54111b895aa0"
    end

    resource "pillow" do
      url "https://files.pythonhosted.org/packages/84/a1/be060135d85187b25fa8b2573786c0e45c62ae27527fff5257675eb97f4a/pillow-13.0.0-cp314-cp314-macosx_10_15_x86_64.whl"
      sha256 "49c12af515073e9bf511e4ef736743bf70d531a643668722279314b937742ba4"
    end

    resource "pypdfium2" do
      url "https://files.pythonhosted.org/packages/09/de/9e7eda3ee1c00228d72f7fc53a370d76eed51fe5fea25debc428ac684e35/pypdfium2-5.15.2-py3-none-macosx_13_0_x86_64.whl"
      sha256 "7f296a298074d76fb7c3d1ecb80d7097a96778bf0ad9c5c48a0170e56e2c6821"
    end
  end

  resource "platformdirs" do
    url "https://files.pythonhosted.org/packages/f8/46/3737af9f971f3934794103256d7f1ed6200a62be0c7b7ff09ac4cf6b3422/platformdirs-4.14.7-py3-none-any.whl"
    sha256 "391513b74707c42335fff3ea17eaac657a7ee9ffcadd809634d34ea594d0122c"
  end

  resource "pyobjc-core" do
    url "https://files.pythonhosted.org/packages/41/a5/463dc32a6c32cff57b4678298a13cd830d7ab09cfec3d7e80f20a2f414fd/pyobjc_core-13.0-cp314-cp314-macosx_10_15_universal2.whl"
    sha256 "fe470bd7b8163b4b8d216b1ebe5b227f01c0fa1c4e0085d7ccade269dec02bb0"
  end

  resource "pyobjc-framework-Cocoa" do
    url "https://files.pythonhosted.org/packages/b4/bb/f683ec329180e1931c8d592c882defebca8810e019cf4bc8727fa36b7d89/pyobjc_framework_cocoa-13.0-cp314-cp314-macosx_10_15_universal2.whl"
    sha256 "88be6d452e7531f695ce6d41428aa74bcaade9ddbc50af592419b9f2fbb7c879"
  end

  resource "pyobjc-framework-CoreML" do
    url "https://files.pythonhosted.org/packages/63/bc/b4d271a3f295dc03926e1ef2a3e14140f77c9227ee55be2f4efcac896728/pyobjc_framework_coreml-13.0-cp314-cp314-macosx_10_15_universal2.whl"
    sha256 "de28b771adc331f875bd755b0873a95895fe668eb22b9215a3bb71747f77c445"
  end

  resource "pyobjc-framework-Quartz" do
    url "https://files.pythonhosted.org/packages/a4/4c/54f6d14e1e78543dfc146f04fc4f11897a937530cec256a487803437f137/pyobjc_framework_quartz-13.0-cp314-cp314-macosx_10_15_universal2.whl"
    sha256 "ea179def24ffbdd61e43e7c33a0cb2b2d79c7cb39fa8d212ab87c964702e5f87"
  end

  resource "pyobjc-framework-Vision" do
    url "https://files.pythonhosted.org/packages/6d/d0/e76f1d66875302e9c15db7c008d061b970b659fba6792bafc4bff13cc220/pyobjc_framework_vision-13.0-cp314-cp314-macosx_10_15_universal2.whl"
    sha256 "cef65bfbb399fcebb755ee79f6ec3aab78c925292073ae8daf4244bdd85ed938"
  end

  def install
    venv = virtualenv_create(libexec, "python3.14")
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
    assert_match version.to_s, shell_output("#{bin}/rga-ocr --version")
    assert_match(/vision\s+yes/, shell_output("#{bin}/rga-ocr --engines"))
  end
end
