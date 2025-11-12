# CLI Commands Guide

This folder contains the CLI implementation for the Malevich SDK using Typer.

## Structure

```
cli/
├── __init__.py          # Main CLI app entry point
└── commands/
    ├── __init__.py      # Commands module
    └── example.py       # Example command (template)
```

## Adding a New Command

### Option 1: Simple Command (Single Function)

Create a new file in `commands/` (e.g., `commands/my_command.py`):

```python
import typer

def my_command(
    name: str = typer.Argument(..., help="Description"),
    flag: bool = typer.Option(False, "--flag", help="A flag"),
) -> None:
    """Command description."""
    typer.echo(f"Running command with {name}")
```

Then register it in `cli/__init__.py`:

```python
from malevich_sdk.cli.commands.my_command import my_command

app.command()(my_command)
```

### Option 2: Command Group (Multiple Related Commands)

Create a new file in `commands/` (e.g., `commands/my_group.py`):

```python
import typer

my_group_app = typer.Typer(name="my-group", help="My command group")

@my_group_app.command()
def subcommand1() -> None:
    """First subcommand."""
    typer.echo("Subcommand 1")

@my_group_app.command()
def subcommand2() -> None:
    """Second subcommand."""
    typer.echo("Subcommand 2")
```

Then register it in `cli/__init__.py`:

```python
from malevich_sdk.cli.commands.my_group import my_group_app

app.add_typer(my_group_app)
```

## Running the CLI

After installing the package, you can run:

```bash
malevich-sdk --help
malevich-sdk example hello John --count 3
```

## Typer Documentation

For more information on Typer, see: https://typer.tiangolo.com/

