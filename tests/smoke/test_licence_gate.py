"""Smoke tests for licence gate functionality."""

from unittest.mock import patch

import pytest

from alfred.scripts.licence_gate import (
    
,
    _normalise,
    main,
    normalize_licence,
    validate_licences,
)

@pytest.mark.smoke_licence
def test_normalize_licence():
    """Test licence name normalization."""
    assert normalize_licence("MIT License") == "MIT"
    assert normalize_licence("Apache Software License") == "Apache-2.0"
    assert normalize_licence("Unknown") == "Unknown"

@pytest.mark.smoke_licence
def test_normalise_composite_licences():
    """Test _normalise function for composite licence strings."""
    assert _normalise("Apache Software License; MIT License") == [
        "Apache Software License",
        "MIT License",
    ]
    assert _normalise("MIT, BSD") == ["MIT", "BSD"]
    assert _normalise("UNKNOWN") == ["UNKNOWN"]
    assert _normalise("unknown") == ["UNKNOWN"]
    assert _normalise("") == []

@pytest.mark.smoke_licence
@patch("alfred.scripts.licence_gate.get_package_licences")
@patch("alfred.scripts.licence_gate.load_licence_waivers")
def test_validate_licences_allowed(mock_waivers, mock_packages):
    """Test validation when all licences are allowed."""
    mock_packages.return_value = [{"Name": "requests", "License": "Apache-2.0"}]
    mock_waivers.return_value = set()

    is_compliant, violations = validate_licences()
    assert is_compliant is True
    assert violations == []

@pytest.mark.smoke_licence
@patch("alfred.scripts.licence_gate.get_package_licences")
@patch("alfred.scripts.licence_gate.load_licence_waivers")
def test_validate_licences_violations(mock_waivers, mock_packages):
    """Test validation with licence violations."""
    mock_packages.return_value = [{"Name": "bad-package", "License": "GPL-3.0"}]
    mock_waivers.return_value = set()

    is_compliant, violations = validate_licences()
    assert is_compliant is False
    assert violations == [("bad-package", "GPL-3.0")]

@pytest.mark.smoke_licence
@pytest.mark.parametrize(
    "packages,expected_exit",
    [
        # Clean environment - should pass
        ([{"Name": "requests", "License": "Apache-2.0"}], 0),
        # Composite licence with allowed parts - should pass
        ([{"Name": "structlog", "License": "Apache Software License; MIT License"}], 0),
        # UNKNOWN licence for safe package - should pass
        ([{"Name": "urllib3", "License": "UNKNOWN"}], 0),
        # Disallowed licence - should fail
        ([{"Name": "badlib", "License": "GPL-3.0"}], 1),
        # UNKNOWN licence for unsafe package - should fail
        ([{"Name": "unknown-pkg", "License": "UNKNOWN"}], 1),
    ],
)
@patch("alfred.scripts.licence_gate.get_package_licences")
@patch("alfred.scripts.licence_gate.load_licence_waivers")
def test_main_exit_codes(mock_waivers, mock_packages, packages, expected_exit):
    """Test main function exit codes for different scenarios."""
    mock_packages.return_value = packages
    mock_waivers.return_value = set()

    if expected_exit == 0:
        # Should not raise SystemExit for clean environment
        main()
    else:
        # Should raise SystemExit for violations
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == expected_exit
