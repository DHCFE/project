"""Vendored Screenpipe source and bundled binary management."""

from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENDORED_SCREENPIPE_ROOT = PROJECT_ROOT / "third_party" / "screenpipe"
VENDORED_CARGO_TOML = VENDORED_SCREENPIPE_ROOT / "Cargo.toml"
VENDORED_TARGET_DIR = VENDORED_SCREENPIPE_ROOT / "target"
BUNDLED_BIN_ROOT = MODULE_ROOT / "bin"


def executable_name() -> str:
    return "screenpipe.exe" if platform.system() == "Windows" else "screenpipe"


def platform_tag() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()

    arch_aliases = {
        "x86_64": "x64",
        "amd64": "x64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    return f"{system}-{arch_aliases.get(machine, machine)}"


def vendored_source_exists() -> bool:
    return VENDORED_CARGO_TOML.exists()


def cargo_available() -> bool:
    return shutil.which("cargo") is not None


def rustup_available() -> bool:
    return shutil.which("rustup") is not None


def bundled_binary_dir() -> Path:
    return BUNDLED_BIN_ROOT / platform_tag()


def bundled_binary_path() -> Path | None:
    path = bundled_binary_dir() / executable_name()
    if path.exists():
        return path
    legacy_path = BUNDLED_BIN_ROOT / executable_name()
    if legacy_path.exists():
        return legacy_path
    return None


def local_build_binary_paths() -> list[Path]:
    exe = executable_name()
    return [
        VENDORED_TARGET_DIR / "release-dev" / exe,
        VENDORED_TARGET_DIR / "release" / exe,
        VENDORED_TARGET_DIR / "debug" / exe,
    ]


def preferred_binary_paths() -> list[Path]:
    paths: list[Path] = []
    bundled = bundled_binary_path()
    if bundled is not None:
        paths.append(bundled)
    paths.extend(local_build_binary_paths())
    return paths


def vendored_binary_path() -> Path | None:
    for path in preferred_binary_paths():
        if path.exists():
            return path
    return None


def ensure_vendored_build(profile: str = "release-dev") -> Path | None:
    if not vendored_source_exists() or not cargo_available():
        return None

    command = [
        "cargo",
        "build",
        "--manifest-path",
        str(VENDORED_CARGO_TOML),
        "-p",
        "screenpipe-engine",
        "--bin",
        "screenpipe",
        "--profile",
        profile,
    ]
    try:
        subprocess.run(command, check=True, cwd=PROJECT_ROOT)
    except Exception:
        return None
    return vendored_binary_path()


def install_bundled_binary(source: Path | None = None) -> Path | None:
    binary = source or vendored_binary_path()
    if binary is None or not binary.exists():
        return None
    target_dir = bundled_binary_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / executable_name()
    shutil.copy2(binary, target)
    target.chmod(target.stat().st_mode | 0o111)
    return target


def launch_vendored_screenpipe(
    screenpipe_url: str,
    auto_build: bool = False,
    background: bool = True,
) -> bool:
    binary = vendored_binary_path()
    if binary is None and auto_build:
        binary = ensure_vendored_build()
    if binary is None:
        return False

    port = screenpipe_url.rsplit(":", 1)[-1].strip("/")
    command = [
        str(binary),
        "record",
        "--port",
        port,
        "--disable-audio",
        "--disable-telemetry",
    ]
    try:
        popen_kwargs = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if background:
            popen_kwargs["start_new_session"] = True
        subprocess.Popen(command, cwd=VENDORED_SCREENPIPE_ROOT, **popen_kwargs)
    except Exception:
        return False
    return True
