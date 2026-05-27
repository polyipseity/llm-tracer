"""Shell completion helpers for the `llm-tracer` CLI."""

from enum import StrEnum
from pathlib import Path
from platform import system

import typer.completion

"""Public symbols exported by this module."""
__all__ = (
    "CompletionShell",
    "install_shell_completion",
    "render_shell_completion",
)


"""Console-script name used in generated completion scripts."""
_PROG_NAME = "llm-tracer"


"""Environment variable consumed by Click/Typer shell completion."""
_COMPLETE_VAR = "_LLM_TRACER_COMPLETE"


class CompletionShell(StrEnum):
    """Supported shells for completion script generation and installation."""

    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    POWERSHELL = "powershell"
    PWSH = "pwsh"


def _install_shell_name(shell: CompletionShell) -> str:
    """Return the shell name Typer should use for installation."""

    if shell is CompletionShell.POWERSHELL and system() != "Windows":
        return CompletionShell.PWSH.value
    return shell.value


def render_shell_completion(shell: CompletionShell) -> str:
    """Return the completion script for a specific shell."""

    return typer.completion.get_completion_script(
        prog_name=_PROG_NAME,
        complete_var=_COMPLETE_VAR,
        shell=shell.value,
    )


def install_shell_completion(shell: CompletionShell) -> tuple[str, Path]:
    """Install shell completion for a specific shell.

    Returns the installed shell name and the path that received the completion
    setup.
    """

    installed_shell, target_path = typer.completion.install(
        shell=_install_shell_name(shell),
        prog_name=_PROG_NAME,
        complete_var=_COMPLETE_VAR,
    )
    return installed_shell, Path(target_path)
