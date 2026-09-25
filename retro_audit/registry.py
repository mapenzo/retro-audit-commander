"""Extensible registry of audit tools."""

from collections.abc import Iterable

from retro_audit.contracts import AuditTool


class ToolRegistry:
    """Store uniquely identified tools and expose deterministic iteration."""

    def __init__(self, tools: Iterable[AuditTool]) -> None:
        tool_list = tuple(tools)
        registered = {tool.tool_id: tool for tool in tool_list}
        if len(registered) != len(tool_list):
            raise ValueError("Los identificadores de herramientas deben ser únicos.")
        self._tools = registered

    def get(self, tool_id: str) -> AuditTool | None:
        """Return a tool by ID, or None when it is not registered."""
        return self._tools.get(tool_id)

    def all(self) -> tuple[AuditTool, ...]:
        """Return registered tools in insertion order."""
        return tuple(self._tools.values())
