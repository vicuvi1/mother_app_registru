"""Dialog configurare range-uri min/max per coloană."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.constants_manager import get_all_etichete, get_range_config, set_range


class RangeConfigDialog(QDialog):
    def __init__(
        self,
        parte: str,
        numeric_columns: list[str],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.parte = parte
        self.numeric_columns = numeric_columns
        self.setWindowTitle("Configurează range-uri — generare automată")
        self.setMinimumSize(620, 520)
        self.resize(680, 560)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Setați min/max pentru fiecare coloană numerică.\n"
                "Generarea automată va respecta aceste limite per coloană."
            )
        )

        etichete = get_all_etichete(parte)
        ranges = get_range_config(parte)

        self.table = QTableWidget(len(numeric_columns), 3)
        self.table.setObjectName("dataTable")
        self.table.setHorizontalHeaderLabels(["Coloană", "Min", "Max"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        for row, col_key in enumerate(numeric_columns):
            label = etichete.get(col_key, col_key)
            name_item = QTableWidgetItem(label)
            name_item.setFlags(
                name_item.flags()
                & ~Qt.ItemFlag.ItemIsEditable
                & ~Qt.ItemFlag.ItemIsSelectable
            )
            name_item.setToolTip(col_key)
            self.table.setItem(row, 0, name_item)

            lo, hi = ranges.get(col_key, (0, 30))
            min_spin = QSpinBox()
            min_spin.setRange(0, 9999)
            min_spin.setValue(lo)
            min_spin.setMinimumWidth(80)
            max_spin = QSpinBox()
            max_spin.setRange(0, 9999)
            max_spin.setValue(hi)
            max_spin.setMinimumWidth(80)
            min_spin.setProperty("col_key", col_key)
            max_spin.setProperty("col_key", col_key)

            min_wrap = QWidget()
            min_layout = QHBoxLayout(min_wrap)
            min_layout.setContentsMargins(6, 2, 6, 2)
            min_layout.addWidget(min_spin)

            max_wrap = QWidget()
            max_layout = QHBoxLayout(max_wrap)
            max_layout.setContentsMargins(6, 2, 6, 2)
            max_layout.addWidget(max_spin)

            self.table.setCellWidget(row, 1, min_wrap)
            self.table.setCellWidget(row, 2, max_wrap)

        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(0, 280)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self.table)
        layout.addWidget(scroll)

        count_label = QLabel(f"{len(numeric_columns)} coloane configurabile")
        count_label.setObjectName("pageSubheading")
        layout.addWidget(count_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_btn:
            save_btn.setText("Salvează range-urile")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        for row in range(self.table.rowCount()):
            min_w = self.table.cellWidget(row, 1)
            max_w = self.table.cellWidget(row, 2)
            if min_w is None or max_w is None:
                continue
            min_spin = min_w.findChild(QSpinBox)
            max_spin = max_w.findChild(QSpinBox)
            if min_spin is None or max_spin is None:
                continue
            col_key = min_spin.property("col_key")
            min_val = min_spin.value()
            max_val = max_spin.value()
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            set_range(self.parte, col_key, min_val, max_val)
        self.accept()
