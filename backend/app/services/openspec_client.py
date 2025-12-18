"""OpenSpec CLI wrapper service."""

import asyncio
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings

settings = get_settings()


class CLIError(Exception):
    """Base exception for CLI errors."""

    def __init__(self, message: str, stdout: str = "", stderr: str = "", return_code: int = 1):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code


class CLITimeoutError(CLIError):
    """CLI command timed out."""

    pass


@dataclass
class CLIResult:
    """Result from CLI command execution."""

    success: bool
    stdout: str
    stderr: str
    return_code: int


@dataclass
class ValidationResult:
    """Parsed validation result."""

    passed: bool
    errors: list[str]
    warnings: list[str]
    output: str


class OpenSpecClient:
    """Wrapper for OpenSpec CLI commands."""

    def __init__(self, timeout: int | None = None):
        self.timeout = timeout or settings.openspec_timeout

    async def _run_command(
        self,
        cmd: list[str],
        cwd: str | Path | None = None,
    ) -> CLIResult:
        """Execute CLI command asynchronously."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout,
            )

            return CLIResult(
                success=process.returncode == 0,
                stdout=stdout.decode("utf-8"),
                stderr=stderr.decode("utf-8"),
                return_code=process.returncode or 0,
            )

        except asyncio.TimeoutError:
            process.kill()
            raise CLITimeoutError(
                f"Command timed out after {self.timeout}s: {' '.join(cmd)}"
            )

    async def _run_command_streaming(
        self,
        cmd: list[str],
        cwd: str | Path | None = None,
    ) -> AsyncIterator[str]:
        """Execute CLI command with streaming output."""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )

        async def read_stream():
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                yield line.decode("utf-8").rstrip()

        async for line in read_stream():
            yield line

        await process.wait()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(CLITimeoutError),
    )
    async def init_project(self, path: str | Path, standard: str) -> CLIResult:
        """Initialize OpenSpec project.

        Runs: openspec init --tools none
        Note: The compliance standard is stored in the database, not in openspec.
        """
        cmd = ["openspec", "init", "--tools", "none"]
        return await self._run_command(cmd, cwd=path)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(CLITimeoutError),
    )
    async def validate_change(
        self,
        path: str | Path,
        proposal_name: str,
        strict: bool = True,
    ) -> ValidationResult:
        """Validate a change proposal.

        Runs: openspec validate {proposal_name} [--strict]
        """
        cmd = ["openspec", "validate", proposal_name]
        if strict:
            cmd.append("--strict")

        result = await self._run_command(cmd, cwd=path)

        # Parse validation output
        errors = []
        warnings = []

        for line in result.stdout.split("\n"):
            line_lower = line.lower()
            if "error" in line_lower:
                errors.append(line.strip())
            elif "warning" in line_lower:
                warnings.append(line.strip())

        return ValidationResult(
            passed=result.success,
            errors=errors,
            warnings=warnings,
            output=result.stdout + result.stderr,
        )

    async def validate_change_streaming(
        self,
        path: str | Path,
        proposal_name: str,
        strict: bool = True,
    ) -> AsyncIterator[str]:
        """Validate with streaming output."""
        cmd = ["openspec", "validate", proposal_name]
        if strict:
            cmd.append("--strict")

        async for line in self._run_command_streaming(cmd, cwd=path):
            yield line

    async def list_changes(self, path: str | Path) -> CLIResult:
        """List active changes.

        Runs: openspec list
        """
        cmd = ["openspec", "list"]
        return await self._run_command(cmd, cwd=path)

    async def show_change(
        self,
        path: str | Path,
        change_id: str,
        json_output: bool = False,
    ) -> CLIResult:
        """Show change details.

        Runs: openspec show {change_id} [--json]
        """
        cmd = ["openspec", "show", change_id]
        if json_output:
            cmd.append("--json")
        return await self._run_command(cmd, cwd=path)

    async def archive_change(
        self,
        path: str | Path,
        change_id: str,
        skip_specs: bool = False,
    ) -> CLIResult:
        """Archive a completed change.

        Runs: openspec archive {change_id} --yes [--skip-specs]
        """
        cmd = ["openspec", "archive", change_id, "--yes"]
        if skip_specs:
            cmd.append("--skip-specs")
        return await self._run_command(cmd, cwd=path)


# Singleton instance
openspec_client = OpenSpecClient()
