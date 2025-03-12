from collections.abc import Callable as CallableABC
from typing import Callable as CallableTyping

from aiohappyeyeballs.types import Callable


def test_callable_import_from_typing():
    """
    Test that Callable is imported from typing.

    PY3.9: https://github.com/python/cpython/issues/87131
    """
    assert Callable is CallableTyping
    assert Callable is not CallableABC
