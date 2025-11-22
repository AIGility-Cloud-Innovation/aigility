"""
Compatibility alias package for end-users to `import memory` instead of `import timem`.

This package re-exports the public API from the `timem` package.
Users can use `import memory` as an alias to `import timem`.
"""

# Import all public symbols from timem
from timem import *

# Explicitly import metadata and re-export them
from timem import (
    __version__,
    __author__,
    __email__,
    __description__,
    __all__ as _timem_all__,
)

# Use the same __all__ as timem to maintain consistency
__all__ = _timem_all__



