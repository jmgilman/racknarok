"""
Shared context and state management for orchestrator commands.

This module defines the OrchestratorContext class that holds shared state
across commands, and provides decorators for accessing it.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

import click


@dataclass
class OrchestratorContext:
    """
    Shared context object passed between CLI commands.

    Attributes:
        verbose: Enable verbose output
        debug: Enable debug mode
        esc_config: Loaded Pulumi ESC configuration (lazy-loaded)
        ssh_agent_setup: Whether SSH agent has been configured
    """

    verbose: bool = False
    debug: bool = False
    esc_config: Optional[dict[str, Any]] = None
    ssh_agent_setup: bool = False

    # Additional state can be added as needed
    _cache: dict[str, Any] = field(default_factory=dict)

    def get_cached(self, key: str) -> Any:
        """Get a value from the context cache."""
        return self._cache.get(key)

    def set_cached(self, key: str, value: Any) -> None:
        """Set a value in the context cache."""
        self._cache[key] = value


# Custom decorator to pass OrchestratorContext to commands
pass_orchestrator_context = click.make_pass_decorator(OrchestratorContext, ensure=True)
