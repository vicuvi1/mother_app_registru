"""Verificare configurare PyInstaller."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_pyinstaller_spec_exists():
    spec = ROOT / "registru.spec"
    assert spec.is_file()
    text = spec.read_text(encoding="utf-8")
    assert "main.py" in text
    assert "RegistruDigital" in text


def test_build_script_exists():
    bat = ROOT / "build.bat"
    assert bat.is_file()
    assert "pyinstaller" in bat.read_text(encoding="utf-8").lower()
