"""Feste Eingaben fuer Tests, unabhaengig vom Nutzerprofil."""

from pathlib import Path

import pytest

from ted import Profile, load_profile


@pytest.fixture
def profile_path() -> Path:
    return Path(__file__).parent / "fixtures" / "search-profile.toml"


@pytest.fixture
def profile(profile_path: Path) -> Profile:
    return load_profile(profile_path)
