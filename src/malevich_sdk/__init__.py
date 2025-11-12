from malevich_sdk.modelling.function import function
from malevich_sdk.modelling.file import File
from malevich_sdk.modelling.arguments import RunContext, Input, Config, InputGroup
from malevich_sdk.modelling.group import Group
from malevich_sdk.core_api.run import run, runflow, runlocal
from malevich_sdk.core_api.credentials import with_user
from malevich_app.square import Context

__all__ = [
    'function', 'RunContext', 'Input', 'Config', 'InputGroup', 'run', 'Group', 'File', 'Context', 'with_user',
    'runflow', 'runlocal'
]


def main() -> None:
    """Main entry point for the CLI application."""
    from malevich_sdk.cli import main as cli_main
    cli_main()