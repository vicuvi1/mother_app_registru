"""Pagină de bază pentru Părțile registrului — compune mixin-urile."""

from PyQt5.QtWidgets import QWidget

from ui.parts.mixins.cache_mixin import PartCacheMixin
from ui.parts.mixins.data_mixin import PartDataMixin
from ui.parts.mixins.export_mixin import PartExportMixin
from ui.parts.mixins.ui_mixin import PartUiMixin


class PartPageBase(PartUiMixin, PartCacheMixin, PartDataMixin, PartExportMixin, QWidget):
    """Pagină reutilizabilă pentru o Parte din registru (daily | monthly | events | crud)."""
