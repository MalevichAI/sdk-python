"""Example CLI command to demonstrate the pattern.

This file serves as a template for creating new CLI commands.
"""

import typer

# Create a command group (optional, for organizing related commands)
example_app = typer.Typer(name="example", help="Example commands")


@example_app.command()
def hello(
    name: str = typer.Argument(..., help="Name to greet"),
    count: int = typer.Option(1, "--count", "-c", help="Number of times to greet"),
    uppercase: bool = typer.Option(False, "--uppercase", "-u", help="Use uppercase"),
) -> None:
    """Say hello to someone.
    
    This is an example command showing how to:
    - Use arguments (required positional)
    - Use options (optional flags)
    - Use boolean flags
    """
    message = f"Hello, {name}!"
    if uppercase:
        message = message.upper()
    
    for _ in range(count):
        typer.echo(message)


# To register this command group, add this to cli/__init__.py:
# from malevich_sdk.cli.commands.example import example_app
# app.add_typer(example_app)

