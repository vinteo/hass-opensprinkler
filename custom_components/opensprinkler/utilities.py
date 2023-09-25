"""Utility functions"""


@staticmethod
def is_set(x, n):
    """Test for nth bit set."""
    return x & 1 << n != 0
