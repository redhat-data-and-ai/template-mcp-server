"""Load MCP tools from YAML config and build FastMCP-ready callables."""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any, Type, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()

TYPE_ALIASES: dict[str, type] = {
    "str": str,
    "string": str,
    "float": float,
    "int": int,
    "integer": int,
    "bool": bool,
    "boolean": bool,
}


class ToolParamConfig(BaseModel):
    """Schema for a single tool parameter declared in YAML."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str = "str"
    required: bool = True
    default: Any = None
    description: str = ""

    def python_type(self) -> Type[Any]:
        """Map the YAML type string to a Python type for FastMCP introspection."""
        normalized = self.type.lower()
        if normalized in {"list", "array", "list[str]", "array[string]"}:
            return list[str]
        return TYPE_ALIASES.get(normalized, str)


class AgentMetadata(BaseModel):
    """Agent-facing metadata for tool discovery and routing."""

    model_config = ConfigDict(extra="forbid")

    usecase: str = ""
    instructions: str = ""
    input_description: str = ""
    output_description: str = ""
    examples: list[str] = Field(default_factory=list)
    prerequisites: str = "none"
    related_tools: list[str] = Field(default_factory=list)


class ToolConfig(BaseModel):
    """Full tool definition loaded from a YAML file."""

    model_config = ConfigDict(extra="forbid")

    name: str
    enabled: bool = True
    handler: str
    display_name: str
    description: str
    params: list[ToolParamConfig] = Field(default_factory=list)
    agent: AgentMetadata = Field(default_factory=AgentMetadata)


def default_tools_config_path() -> Path:
    """Return the default tools config directory bundled with the package."""
    return Path(__file__).resolve().parent.parent / "config" / "tools"


def resolve_tools_config_path(config_path: Path | str | None = None) -> Path:
    """Resolve the tools config directory from override or settings."""
    if config_path is not None:
        return Path(config_path)

    from template_mcp_server.src.settings import settings

    config_override = settings.MCP_TOOLS_CONFIG_PATH
    if isinstance(config_override, str) and config_override.strip():
        return Path(config_override)

    return default_tools_config_path()


def load_tool_configs(config_path: Path | str | None = None) -> list[ToolConfig]:
    """Load and validate all tool YAML files from the config directory."""
    tools_dir = resolve_tools_config_path(config_path)
    if not tools_dir.is_dir():
        raise FileNotFoundError(f"Tools config directory not found: {tools_dir}")

    configs: list[ToolConfig] = []
    seen_names: set[str] = set()

    for yaml_file in sorted(tools_dir.glob("*.yaml")):
        with yaml_file.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)

        if not data:
            continue

        config = ToolConfig.model_validate(data)
        if config.name in seen_names:
            raise ValueError(f"Duplicate tool name '{config.name}' in {yaml_file}")
        seen_names.add(config.name)
        configs.append(config)

    if not configs:
        raise ValueError(f"No tool configs found in {tools_dir}")

    return configs


def import_handler(handler: str) -> Callable[..., Any]:
    """Import a handler callable from a module:attr string."""
    module_path, _, attr = handler.partition(":")
    if not module_path or not attr:
        raise ValueError(f"Invalid handler '{handler}': expected 'module:attr'")

    module = importlib.import_module(module_path)
    fn = getattr(module, attr, None)
    if fn is None or not callable(fn):
        raise ValueError(f"Handler '{handler}' is not callable")
    return fn


def _format_related_tools(related: list[str]) -> str:
    if not related:
        return "None"
    return ", ".join(related)


def build_agent_docstring(config: ToolConfig) -> str:
    """Build the agent metadata docstring from YAML fields."""
    agent = config.agent
    examples = ", ".join(agent.examples) if agent.examples else f"{config.name}()"
    return "\n".join(
        [
            config.description,
            "",
            f"TOOL_NAME={config.name}",
            f"DISPLAY_NAME={config.display_name}",
            f"USECASE={agent.usecase}",
            f"INSTRUCTIONS={agent.instructions.strip()}",
            f"INPUT_DESCRIPTION={agent.input_description}",
            f"OUTPUT_DESCRIPTION={agent.output_description}",
            f"EXAMPLES={examples}",
            f"PREREQUISITES={agent.prerequisites}",
            f"RELATED_TOOLS={_format_related_tools(agent.related_tools)}",
        ]
    )


def _build_signature(
    config: ToolConfig, return_annotation: Any = dict[str, Any]
) -> inspect.Signature:
    parameters: list[inspect.Parameter] = []
    for param in config.params:
        annotation = param.python_type()
        if param.required and param.default is None:
            default = inspect.Parameter.empty
        else:
            default = param.default
        parameters.append(
            inspect.Parameter(
                param.name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default,
                annotation=annotation,
            )
        )
    return inspect.Signature(parameters, return_annotation=dict[str, Any])


def _bind_and_call(
    signature: inspect.Signature, handler: Callable[..., Any], *args: Any, **kwargs: Any
) -> Any:
    bound = signature.bind_partial(*args, **kwargs)
    bound.apply_defaults()
    return handler(**bound.arguments)


async def _bind_and_call_async(
    signature: inspect.Signature, handler: Callable[..., Any], *args: Any, **kwargs: Any
) -> Any:
    bound = signature.bind_partial(*args, **kwargs)
    bound.apply_defaults()
    return await handler(**bound.arguments)


def _apply_wrapper_metadata(
    wrapper: Callable[..., Any],
    config: ToolConfig,
    signature: inspect.Signature,
    docstring: str,
    annotations: dict[str, Any],
) -> Callable[..., Any]:
    wrapper.__name__ = config.name
    wrapper.__doc__ = docstring
    wrapper.__signature__ = signature  # type: ignore[attr-defined]
    wrapper.__annotations__ = annotations
    return wrapper


def build_tool_callable(
    config: ToolConfig, handler: Callable[..., Any]
) -> Callable[..., Any]:
    """Wrap a handler with YAML-driven name, signature, and docstring."""
    handler_return = inspect.signature(handler).return_annotation
    if handler_return is inspect.Parameter.empty:
        handler_return = dict[str, Any]
    signature = _build_signature(config, handler_return)
    docstring = build_agent_docstring(config)
    annotations = {param.name: param.python_type() for param in config.params}
    annotations["return"] = handler_return

    if inspect.iscoroutinefunction(handler):

        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _bind_and_call_async(signature, handler, *args, **kwargs)

        return _apply_wrapper_metadata(
            cast(Callable[..., Any], async_wrapper),
            config,
            signature,
            docstring,
            annotations,
        )

    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        return _bind_and_call(signature, handler, *args, **kwargs)

    return _apply_wrapper_metadata(
        sync_wrapper, config, signature, docstring, annotations
    )


def load_tool_registry(
    config_path: Path | str | None = None,
) -> dict[str, Callable[..., Any]]:
    """Load enabled tools from config and return a name -> callable registry."""
    registry: dict[str, Callable[..., Any]] = {}

    for config in load_tool_configs(config_path):
        if not config.enabled:
            logger.info("Skipping disabled tool: %s", config.name)
            continue

        handler = import_handler(config.handler)
        registry[config.name] = build_tool_callable(config, handler)
        logger.debug("Loaded tool from config: %s", config.name)

    if not registry:
        raise ValueError("No enabled tools found in configuration")

    return registry
