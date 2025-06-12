"""Tests for formatter tools."""

import json

import yaml

from alfred.tools.formatter import JsonFormatter, YamlFormatter

class TestJsonFormatter:
    """Tests for JsonFormatter class."""

    def test_format_dict(self) -> None:
        """Test formatting a dictionary as JSON."""
        formatter = JsonFormatter(indent=2)
        data = {"name": "Alfred", "version": 1.0}
        result = formatter.format(data)

        # Verify it's valid JSON
        parsed = json.loads(result)
        assert parsed == data

        # Verify indentation
        assert result.count("\n") > 0

    def test_format_list(self) -> None:
        """Test formatting a list as JSON."""
        formatter = JsonFormatter(indent=2)
        data = [1, 2, 3, {"name": "Alfred"}]
        result = formatter.format(data)

        # Verify it's valid JSON
        parsed = json.loads(result)
        assert parsed == data

    def test_parse_json(self) -> None:
        """Test parsing JSON string."""
        formatter = JsonFormatter()
        json_str = '{"name": "Alfred", "active": true, "items": [1, 2, 3]}'
        result = formatter.parse(json_str)

        assert isinstance(result, dict)
        assert result["name"] == "Alfred"
        assert result["active"] is True
        assert result["items"] == [1, 2, 3]

class TestYamlFormatter:
    """Tests for YamlFormatter class."""

    def test_format_dict(self) -> None:
        """Test formatting a dictionary as YAML."""
        formatter = YamlFormatter()
        data = {"name": "Alfred", "version": 1.0, "config": {"debug": True}}
        result = formatter.format(data)

        # Verify it's valid YAML
        parsed = yaml.safe_load(result)
        assert parsed == data

        # Verify format (not using flow style)
        assert ":" in result
        assert result.count("\n") > 0

    def test_format_list(self) -> None:
        """Test formatting a list as YAML."""
        formatter = YamlFormatter()
        data = [1, 2, 3, {"name": "Alfred"}]
        result = formatter.format(data)

        # Verify it's valid YAML
        parsed = yaml.safe_load(result)
        assert parsed == data

    def test_parse_yaml(self) -> None:
        """Test parsing YAML string."""
        formatter = YamlFormatter()
        yaml_str = """
        name: Alfred
        active: true
        items:
          - 1
          - 2
          - 3
        """
        result = formatter.parse(yaml_str)

        assert isinstance(result, dict)
        assert result["name"] == "Alfred"
        assert result["active"] is True
        assert result["items"] == [1, 2, 3]
