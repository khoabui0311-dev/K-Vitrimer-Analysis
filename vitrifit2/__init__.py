"""VitriFit 2.0 experimental persistent research platform.

Existing v1 modules remain authoritative for scientific computation and plotting
until parity and regression tests are complete.
"""

from .persistence import VitriFitStore

__all__ = ["VitriFitStore"]
