"""CLI commands for managing credentials."""

import typer
from pathlib import Path
from typing import Optional
from rich import print as rprint
from rich.table import Table
from rich.console import Console

from malevich_sdk.usp.credstore import UserCredentialsStore

console = Console()
creds_app = typer.Typer(name="creds", help="Manage credentials")


def _get_store(path: Optional[str] = None) -> UserCredentialsStore:
    """Get credentials store with optional custom path."""
    config_dir = Path(path) if path else None
    return UserCredentialsStore(config_dir=config_dir)


# ========== ADD COMMANDS ==========

@creds_app.command("add")
def add(
    cred_type: str = typer.Argument(..., help="Credential type: 'core' or 'image'"),
    registry: Optional[str] = typer.Argument(None, help="Registry reference (for image type)"),
    login: Optional[str] = typer.Argument(None, help="Username/login"),
    password: Optional[str] = typer.Argument(None, help="Password/token"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing credentials"),
    path: Optional[str] = typer.Option(None, "--path", help="Custom config directory path"),
):
    """Add credentials.
    
    Examples:
        malevich-sdk creds add image ghcr.io/malevichai myuser mytoken
        malevich-sdk creds add core myuser mypass --overwrite
    """
    store = _get_store(path)
    
    if cred_type == "image":
        # For image: need registry, login, password
        if not all([registry, login, password]):
            console.print("[red]Error:[/red] For image credentials, provide: <REGISTRY> <LOGIN> <PASSWORD>")
            raise typer.Exit(1)
        
        store.add_image_credentials(
            ref=registry,
            user=login,
            token=password,
            replace=overwrite
        )
        console.print(f"[green]✓[/green] Image credentials added for [cyan]{registry}[/cyan]")
        
    elif cred_type == "core":
        # For core: registry is actually login, login is password
        if not all([registry, login]):
            console.print("[red]Error:[/red] For core credentials, provide: <LOGIN> <PASSWORD>")
            raise typer.Exit(1)
        
        actual_login = registry
        actual_password = login
        
        # Prompt for host if not using default
        host = typer.prompt("Host (press Enter for default)", default="https://core.mtp.group")
        
        store.add_core_credentials(
            user=actual_login,
            password=actual_password,
            host=host,
            replace=overwrite
        )
        console.print(f"[green]✓[/green] Core credentials added for [cyan]{actual_login}[/cyan]")
        
    else:
        console.print(f"[red]Error:[/red] Unknown credential type '{cred_type}'. Use 'core' or 'image'.")
        raise typer.Exit(1)


# ========== LIST COMMANDS ==========

@creds_app.command("list")
def list_creds(
    cred_type: str = typer.Argument(..., help="Credential type: 'core' or 'image'"),
    path: Optional[str] = typer.Option(None, "--path", help="Custom config directory path"),
):
    """List stored credentials.
    
    Examples:
        malevich-sdk creds list image
        malevich-sdk creds list core
    """
    store = _get_store(path)
    
    if cred_type == "image":
        all_creds = store.list_all()
        image_creds = [c for c in all_creds if c["type"] == "image"]
        
        if not image_creds:
            console.print("[yellow]No image credentials found[/yellow]")
            return
        
        table = Table(title="Image Registry Credentials", show_header=True)
        table.add_column("Registry", style="cyan")
        table.add_column("User", style="green")
        
        for cred in image_creds:
            table.add_row(cred["ref"], cred["user"])
        
        console.print(table)
        
    elif cred_type == "core":
        all_creds = store.list_all()
        core_creds = [c for c in all_creds if c["type"] == "core"]
        
        if not core_creds:
            console.print("[yellow]No core credentials found[/yellow]")
            return
        
        table = Table(title="Core API Credentials", show_header=True)
        table.add_column("User", style="cyan")
        table.add_column("Host", style="green")
        
        for cred in core_creds:
            table.add_row(cred["user"], cred["host"])
        
        console.print(table)
        
    else:
        console.print(f"[red]Error:[/red] Unknown credential type '{cred_type}'. Use 'core' or 'image'.")
        raise typer.Exit(1)


# ========== REMOVE COMMANDS ==========

@creds_app.command("remove")
def remove(
    cred_type: str = typer.Argument(..., help="Credential type: 'image' or 'core'"),
    identifier: str = typer.Argument(..., help="Registry reference (for image) or login (for core)"),
    path: Optional[str] = typer.Option(None, "--path", help="Custom config directory path"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Remove credentials.
    
    Examples:
        malevich-sdk creds remove image ghcr.io/malevichai
        malevich-sdk creds remove core myuser
    """
    store = _get_store(path)
    
    # Confirm deletion unless --yes is provided
    if not yes:
        confirm = typer.confirm(f"Remove {cred_type} credentials for '{identifier}'?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)
    
    if cred_type == "image":
        removed = store.remove_image_credentials(identifier)
        if removed:
            console.print(f"[green]✓[/green] Removed image credentials for [cyan]{identifier}[/cyan]")
        else:
            console.print(f"[yellow]No credentials found for {identifier}[/yellow]")
            
    elif cred_type == "core":
        # For core, we need to check if the identifier matches the user
        core_creds = store.get_core_credentials()
        if core_creds and core_creds.user == identifier:
            removed = store.remove_core_credentials()
            if removed:
                console.print(f"[green]✓[/green] Removed core credentials for [cyan]{identifier}[/cyan]")
            else:
                console.print(f"[yellow]No credentials found[/yellow]")
        else:
            console.print(f"[yellow]No core credentials found for user '{identifier}'[/yellow]")
            
    else:
        console.print(f"[red]Error:[/red] Unknown credential type '{cred_type}'. Use 'core' or 'image'.")
        raise typer.Exit(1)


# ========== ADDITIONAL HELPER COMMANDS ==========

@creds_app.command("clear")
def clear_all(
    path: Optional[str] = typer.Option(None, "--path", help="Custom config directory path"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Remove all stored credentials."""
    if not yes:
        confirm = typer.confirm("Remove ALL credentials?", abort=True)
    
    store = _get_store(path)
    store.clear_all()
    console.print("[green]✓[/green] All credentials cleared")

