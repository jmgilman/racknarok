"""
Sync command for synchronizing config/secrets to Pulumi ESC.

Syncs configuration and SOPS-encrypted secrets from Git to ESC environments.
"""

import json
import subprocess
from pathlib import Path

import click
import pulumi.automation as auto

from orchestrator.context import pass_orchestrator_context, OrchestratorContext


def get_repo_root() -> Path:
    """
    Get the repository root directory.

    Assumes the orchestrator is located at orchestrator/src/orchestrator
    relative to the repo root.
    """
    # Get the directory containing this file
    current_file = Path(__file__).resolve()
    # Navigate up: commands/ -> orchestrator/ -> src/ -> orchestrator/ -> repo_root
    repo_root = current_file.parent.parent.parent.parent.parent
    return repo_root


def get_sops_key_from_esc() -> str:
    """
    Retrieve the SOPS age private key from Pulumi ESC.

    The key is stored in the jmgilman/default/ci environment.

    Returns:
        The SOPS age private key

    Raises:
        click.ClickException: If the key cannot be retrieved
    """
    try:
        # Use the ESC CLI to open the environment and extract the key
        result = subprocess.run(
            ["esc", "env", "open", "jmgilman/default/ci", "--format", "json"],
            capture_output=True,
            text=True,
            check=True,
        )

        env_data = json.loads(result.stdout)
        sops_key = env_data.get("sops", {}).get("private_key")

        if not sops_key:
            raise click.ClickException(
                "SOPS private key not found in ESC environment jmgilman/default/ci"
            )

        return sops_key

    except subprocess.CalledProcessError as e:
        raise click.ClickException(
            f"Failed to retrieve SOPS key from ESC: {e.stderr}"
        )
    except json.JSONDecodeError as e:
        raise click.ClickException(
            f"Failed to parse ESC environment data: {e}"
        )


def run_pulumi_sync(
    work_dir: Path,
    sops_key: str,
    dry_run: bool,
    verbose: bool,
) -> auto.UpResult | auto.PreviewResult:
    """
    Run the Pulumi esc-sync project via Automation API.

    Args:
        work_dir: Path to the pulumi/esc-sync directory
        sops_key: SOPS age private key for decryption
        dry_run: If True, run preview instead of up
        verbose: Enable verbose output

    Returns:
        The result of the Pulumi operation

    Raises:
        click.ClickException: If the operation fails
    """
    try:
        # Create or select the stack
        stack = auto.create_or_select_stack(
            stack_name="prod",
            project_name="esc-sync",
            work_dir=str(work_dir),
            opts=auto.LocalWorkspaceOptions(
                env_vars={
                    "SOPS_AGE_KEY": sops_key,
                }
            ),
        )

        click.echo(f"📦 Stack: {stack.name}")

        # Define output handler
        def output_handler(msg: str) -> None:
            if verbose:
                click.echo(f"  {msg}", nl=False)

        # Run preview or up
        if dry_run:
            click.echo("🔍 Running Pulumi preview...")
            result = stack.preview(on_output=output_handler)
            return result
        else:
            click.echo("🚀 Running Pulumi up...")
            result = stack.up(on_output=output_handler)
            return result

    except auto.StackAlreadyExistsError:
        # This shouldn't happen with create_or_select_stack, but handle it
        raise click.ClickException("Stack already exists (unexpected error)")
    except auto.CommandError as e:
        raise click.ClickException(f"Pulumi command failed:\n{e.stderr}")
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}")


def display_summary(result: auto.UpResult | auto.PreviewResult, dry_run: bool) -> None:
    """
    Display a summary of the Pulumi operation results.

    Args:
        result: The Pulumi operation result
        dry_run: Whether this was a preview operation
    """
    click.echo()
    click.echo("=" * 60)

    if dry_run:
        click.echo("📋 Preview Summary")
    else:
        click.echo("✅ Sync Summary")

    click.echo("=" * 60)

    # For UpResult, we have summary and outputs
    if isinstance(result, auto.UpResult):
        summary = result.summary
        click.echo(f"Status: {summary.result}")

        # Display resource changes
        if summary.resource_changes:
            click.echo("\nResource Changes:")
            for change_type, count in summary.resource_changes.items():
                if count > 0:
                    click.echo(f"  {change_type}: {count}")

        # Display outputs
        if result.outputs:
            click.echo("\nOutputs:")
            for key, output in result.outputs.items():
                if output.secret:
                    click.echo(f"  {key}: [secret]")
                else:
                    click.echo(f"  {key}: {output.value}")

    # For PreviewResult, we have change_summary
    elif isinstance(result, auto.PreviewResult):
        if result.change_summary:
            click.echo("\nProposed Changes:")
            for change_type, count in result.change_summary.items():
                if count > 0:
                    click.echo(f"  {change_type}: {count}")

    click.echo("=" * 60)


@click.command(name="sync-config")
@click.option(
    "--environment",
    "-e",
    multiple=True,
    help="Specific environment(s) to sync (can be specified multiple times)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be synced without making changes",
)
@pass_orchestrator_context
def sync_config(
    ctx: OrchestratorContext,
    environment: tuple[str, ...],
    dry_run: bool,
) -> None:
    """
    Sync configuration and secrets to Pulumi ESC.

    Reads config/esc-mapping.yaml and syncs the specified files to
    their corresponding ESC environments. SOPS-encrypted secrets are
    automatically decrypted before syncing.

    This command wraps the pulumi/esc-sync TypeScript project using
    the Pulumi Automation API, ensuring SOPS is available and the
    age key is properly configured.

    \b
    Example:
        orchestrator sync-config
        orchestrator sync-config --dry-run
        orchestrator sync-config --environment proxmox
    """
    click.echo("🔐 Syncing configuration to Pulumi ESC")
    click.echo()

    if environment:
        click.secho(
            f"⚠️  Environment filtering not yet implemented: {', '.join(environment)}",
            fg="yellow",
        )
        click.echo("   (All environments will be synced)")
        click.echo()

    if dry_run:
        click.echo("🔍 Dry run mode - no changes will be made")
        click.echo()

    # Get repository root
    repo_root = get_repo_root()
    esc_sync_dir = repo_root / "pulumi" / "esc-sync"

    if not esc_sync_dir.exists():
        raise click.ClickException(
            f"ESC sync project not found at: {esc_sync_dir}"
        )

    if ctx.verbose:
        click.echo(f"📁 Repository root: {repo_root}")
        click.echo(f"📁 ESC sync directory: {esc_sync_dir}")
        click.echo()

    # Retrieve SOPS key from ESC
    click.echo("🔑 Retrieving SOPS key from ESC...")
    try:
        sops_key = get_sops_key_from_esc()
        click.secho("✓ SOPS key retrieved", fg="green")
        click.echo()
    except click.ClickException as e:
        click.secho(f"✗ Failed to retrieve SOPS key: {e.format_message()}", fg="red", err=True)
        raise click.Abort()

    # Run the Pulumi sync
    try:
        result = run_pulumi_sync(
            work_dir=esc_sync_dir,
            sops_key=sops_key,
            dry_run=dry_run,
            verbose=ctx.verbose,
        )

        # Display summary
        display_summary(result, dry_run)

        if dry_run:
            click.secho("\n✓ Preview completed successfully", fg="green")
        else:
            click.secho("\n✓ Configuration synced successfully", fg="green")

    except click.ClickException as e:
        click.secho(f"\n✗ Sync failed: {e.format_message()}", fg="red", err=True)
        raise click.Abort()
