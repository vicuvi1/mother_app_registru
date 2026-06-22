"""Teste Sprint III — distribuție, ghid PDF, release CI."""

import importlib.util
import re
import sys
from pathlib import Path

from core.version import APP_VERSION

ROOT = Path(__file__).resolve().parent.parent


def _guide_module():
    path = ROOT / "scripts" / "generate_user_guide.py"
    spec = importlib.util.spec_from_file_location("generate_user_guide", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["generate_user_guide"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_user_guide_generates_pdf(tmp_path):
    mod = _guide_module()
    out = tmp_path / "ghid.pdf"
    path = mod.generate_user_guide_pdf(out)
    assert path.is_file()
    assert path.stat().st_size > 500
    assert path.read_bytes()[:4] == b"%PDF"


def test_user_guide_path_after_generate():
    from core.user_guide import get_user_guide_path, guide_output_path

    mod = _guide_module()
    mod.generate_user_guide_pdf(guide_output_path())
    path = get_user_guide_path()
    assert path is not None
    assert path.name == "ghid_bibliotecar.pdf"


def test_installer_version_matches_app():
    iss = (ROOT / "installer" / "registru.iss").read_text(encoding="utf-8")
    default_ver = re.search(r'#define MyAppVersion "([^"]+)"', iss)
    assert default_ver is not None
    assert default_ver.group(1) == APP_VERSION


def test_spec_includes_user_guide():
    spec = (ROOT / "registru.spec").read_text(encoding="utf-8")
    assert "resources/guides" in spec


def test_release_workflow_exists():
    workflow = ROOT.parent / ".github" / "workflows" / "release.yml"
    assert workflow.is_file()
    text = workflow.read_text(encoding="utf-8")
    assert "pyinstaller" in text.lower()
    assert "action-gh-release" in text


def test_build_scripts_generate_guide():
    for name in ("build.bat", "build_installer.bat"):
        bat = (ROOT / name).read_text(encoding="utf-8")
        assert "generate_user_guide" in bat
