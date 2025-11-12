"""Main CLI application entry point using Typer."""

import typer

# Create the main Typer app
app = typer.Typer(
    name="malevich-sdk",
    help="Malevich SDK CLI",
    add_completion=False,
)

# Import and register command groups here
from malevich_sdk.cli.commands.creds import creds_app
app.add_typer(creds_app)

# Example for single commands:
# from malevich_sdk.cli.commands.my_command import my_command
# app.command()(my_command)


def main() -> None:
    """Main entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()

