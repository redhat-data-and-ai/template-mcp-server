"""Tests for the tools config loader."""

import inspect
from pathlib import Path

import pytest

from template_mcp_server.src import settings as settings_module
from template_mcp_server.src.tools_loader import (
    AgentMetadata,
    ToolConfig,
    build_agent_docstring,
    build_tool_callable,
    default_tools_config_path,
    import_handler,
    load_tool_configs,
    load_tool_registry,
    resolve_tools_config_path,
)

DEEP_AGENT_TOOLS = {
    "calculate_bmi",
    "validate_email",
    "send_email",
    "search_web",
}


class TestToolsLoader:
    """Test YAML-driven tool loading and registration."""

    def test_default_tools_config_path_exists(self):
        path = default_tools_config_path()
        assert path.is_dir()
        assert list(path.glob("*.yaml"))

    def test_load_tool_configs_returns_four_tools(self):
        configs = load_tool_configs()
        names = {config.name for config in configs}
        assert names == DEEP_AGENT_TOOLS

    def test_load_tool_registry_registers_enabled_tools(self):
        registry = load_tool_registry()
        assert set(registry) == DEEP_AGENT_TOOLS

    def test_registry_callable_has_yaml_docstring_metadata(self):
        registry = load_tool_registry()
        bmi = registry["calculate_bmi"]
        assert bmi.__name__ == "calculate_bmi"
        assert "TOOL_NAME=calculate_bmi" in bmi.__doc__
        assert "DISPLAY_NAME=BMI Calculator" in bmi.__doc__

    def test_registry_bmi_wrapper_delegates_to_handler(self):
        registry = load_tool_registry()
        result = registry["calculate_bmi"](height="175", weight="70")
        assert result["status"] == "success"
        assert result["bmi"] > 0

    def test_registry_signature_from_yaml(self):
        registry = load_tool_registry()
        sig = inspect.signature(registry["calculate_bmi"])
        assert list(sig.parameters) == ["height", "weight"]
        assert sig.parameters["height"].annotation is str

    def test_registry_search_web_signature_includes_list_param(self):
        registry = load_tool_registry()
        sig = inspect.signature(registry["search_web"])
        assert list(sig.parameters) == ["queries", "max_results"]
        assert sig.parameters["queries"].annotation == list[str]

    def test_import_handler_invalid_format_raises(self):
        with pytest.raises(ValueError, match="expected 'module:attr'"):
            import_handler("not_a_valid_handler")

    def test_import_handler_missing_callable_raises(self):
        with pytest.raises(ValueError, match="is not callable"):
            import_handler("template_mcp_server.src.tools.bmi_tool:missing_fn")

    def test_load_tool_configs_missing_directory_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="Tools config directory not found"):
            load_tool_configs(tmp_path / "missing")

    def test_load_tool_configs_duplicate_names_raises(self, tmp_path: Path):
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "one.yaml").write_text(
            "name: dup\nenabled: true\nhandler: x:y\ndisplay_name: A\ndescription: A\n"
        )
        (tools_dir / "two.yaml").write_text(
            "name: dup\nenabled: true\nhandler: x:y\ndisplay_name: B\ndescription: B\n"
        )
        with pytest.raises(ValueError, match="Duplicate tool name"):
            load_tool_configs(tools_dir)

    def test_load_tool_registry_skips_disabled_tools(self, tmp_path: Path):
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "calculate_bmi.yaml").write_text(
            (default_tools_config_path() / "calculate_bmi.yaml").read_text()
        )
        (tools_dir / "disabled.yaml").write_text(
            "name: disabled_tool\nenabled: false\n"
            "handler: template_mcp_server.src.tools.bmi_tool:calculate_bmi\n"
            "display_name: Disabled\ndescription: Disabled tool\n"
        )
        registry = load_tool_registry(tools_dir)
        assert set(registry) == {"calculate_bmi"}

    def test_build_agent_docstring_includes_examples(self):
        configs = load_tool_configs()
        bmi = next(c for c in configs if c.name == "calculate_bmi")
        doc = build_agent_docstring(bmi)
        assert 'calculate_bmi("175", "70")' in doc

    @pytest.mark.asyncio
    async def test_async_handler_wrapper_is_coroutine_function(self):
        configs = load_tool_configs()
        search_config = next(c for c in configs if c.name == "search_web")
        handler = import_handler(search_config.handler)
        wrapped = build_tool_callable(search_config, handler)
        assert inspect.iscoroutinefunction(wrapped)

    @pytest.mark.asyncio
    async def test_async_handler_wrapper_delegates_to_handler(self):
        registry = load_tool_registry()
        result = await registry["search_web"](queries=["test query"], max_results=1)
        assert result["status"] == "error"
        assert "TAVILY_API_KEY" in result["error"]

    def test_resolve_tools_config_path_uses_settings_override(
        self, tmp_path: Path, monkeypatch
    ):
        tools_dir = tmp_path / "custom_tools"
        tools_dir.mkdir()
        (tools_dir / "calculate_bmi.yaml").write_text(
            (default_tools_config_path() / "calculate_bmi.yaml").read_text()
        )
        monkeypatch.setattr(
            settings_module.settings, "MCP_TOOLS_CONFIG_PATH", str(tools_dir)
        )
        assert resolve_tools_config_path() == tools_dir

    def test_load_tool_configs_skips_empty_yaml_files(self, tmp_path: Path):
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "empty.yaml").write_text("")
        (tools_dir / "calculate_bmi.yaml").write_text(
            (default_tools_config_path() / "calculate_bmi.yaml").read_text()
        )
        configs = load_tool_configs(tools_dir)
        assert len(configs) == 1
        assert configs[0].name == "calculate_bmi"

    def test_load_tool_configs_raises_when_no_valid_configs(self, tmp_path: Path):
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "empty.yaml").write_text("")
        with pytest.raises(ValueError, match="No tool configs found"):
            load_tool_configs(tools_dir)

    def test_load_tool_registry_raises_when_all_tools_disabled(self, tmp_path: Path):
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "disabled.yaml").write_text(
            "name: disabled_tool\nenabled: false\n"
            "handler: template_mcp_server.src.tools.bmi_tool:calculate_bmi\n"
            "display_name: Disabled\ndescription: Disabled tool\n"
        )
        with pytest.raises(ValueError, match="No enabled tools found"):
            load_tool_registry(tools_dir)

    def test_load_tool_configs_rejects_unknown_yaml_fields(self, tmp_path: Path):
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "bad.yaml").write_text(
            "name: bad_tool\nenabled: true\n"
            "handler: template_mcp_server.src.tools.bmi_tool:calculate_bmi\n"
            "display_name: Bad\ndescription: Bad tool\n"
            "typo_field: oops\n"
        )
        with pytest.raises(Exception, match="extra_forbidden|Extra inputs"):
            load_tool_configs(tools_dir)

    def test_build_agent_docstring_formats_related_tools(self):
        config = ToolConfig(
            name="example",
            handler="x:y",
            display_name="Example",
            description="Example tool",
            agent=AgentMetadata(related_tools=["calculate_bmi", "search_web"]),
        )
        doc = build_agent_docstring(config)
        assert "RELATED_TOOLS=calculate_bmi, search_web" in doc
