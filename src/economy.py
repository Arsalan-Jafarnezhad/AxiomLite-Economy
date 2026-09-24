"""
The public Economy class, composed from three focused pieces:
core.EconomyCore (users/transactions/aggregates), importers.ImportMixin,
and exporters.ExportMixin. Each concern lives in its own small file.
"""

from .core import EconomyCore
from .exporters import ExportMixin
from .importers import ImportMixin


class Economy(EconomyCore, ImportMixin, ExportMixin):
    """Personal economy / money tracking, backed by SQLite."""
