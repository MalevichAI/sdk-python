"""Group class for assembling InputGroups."""

from typing import Any


class Group:
    """Helper class to assemble InputGroups for the run function.
    
    Positional arguments passed to run() are assumed to be InputGroups
    with corresponding titles. Use Group() to assemble these groups.
    
    Args:
        name: The name of the InputGroup (corresponds to the function parameter name)
        **kwargs: Key-value pairs that make up the group's data
        
    Examples:
        ```python
        run(
            "some_function",
            config={},
            Group("from_address", city="Moscow", street="Main St"),
            Group("to_address", city="SPB", street="Nevsky"),
            threshold=0.5  # Goes to default group
        )
        ```
    """
    def __init__(self, name: str, /, **kwargs: Any) -> None:
        self.name = name
        self.data = kwargs

