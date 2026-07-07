"""Auto-completare Masculin/Feminin după 2s de la editarea totalului participanți."""

from __future__ import annotations

from PyQt5.QtCore import QTimer

from core.participant_split import (
    OVERRIDE_PARTICIPANTI_GENDER,
    apply_participant_gender_split,
    validate_participant_gender_value,
)
from ui.widgets.editable_table import EditableTable


class ParticipantGenderSplitMixin:
    """Mixin: total participanți → M/F automat dacă utilizatorul nu editează manual."""

    PARTICIPANTI_TOTAL_KEY = "numar_participanti"
    PARTICIPANTI_M_KEY = "participanti_masculin"
    PARTICIPANTI_F_KEY = "participanti_feminin"
    GENDER_SPLIT_DELAY_MS = 2000

    def _ensure_gender_split_state(self) -> None:
        if not hasattr(self, "_gender_split_timers"):
            self._gender_split_timers: dict[tuple[int, int], QTimer] = {}

    def _make_table(self) -> EditableTable:
        table = super()._make_table()  # type: ignore[misc]
        self._bind_participant_gender_validator(table)
        return table

    def _bind_participant_gender_validator(self, table: EditableTable) -> None:
        total_key = self.PARTICIPANTI_TOTAL_KEY
        m_key = self.PARTICIPANTI_M_KEY
        f_key = self.PARTICIPANTI_F_KEY
        page = self

        def validator(data_row: int, column_key: str, new_value) -> tuple[bool, str]:
            rows = table.get_data_rows()
            if data_row < 0 or data_row >= len(rows):
                return True, ""
            return validate_participant_gender_value(
                rows[data_row],
                column_key,
                new_value,
                total_key=total_key,
                m_key=m_key,
                f_key=f_key,
            )

        table._register_model.set_cell_validator(validator)

    def _on_cell_edited(self, row: int, key: str, value) -> None:
        super()._on_cell_edited(row, key, value)  # type: ignore[misc]
        table = self.sender()
        if table is None:
            return
        self._handle_participant_gender_edit(table, row, key)

    def _handle_participant_gender_edit(
        self, table: EditableTable, row: int, key: str
    ) -> None:
        self._ensure_gender_split_state()
        total_key = self.PARTICIPANTI_TOTAL_KEY
        m_key = self.PARTICIPANTI_M_KEY
        f_key = self.PARTICIPANTI_F_KEY

        if key == total_key:
            table.set_row_extra(row, OVERRIDE_PARTICIPANTI_GENDER, False)
            self._schedule_gender_split(table, row)
        elif key in (m_key, f_key):
            table.set_row_extra(row, OVERRIDE_PARTICIPANTI_GENDER, True)
            self._cancel_gender_split(table, row)

    def _timer_key(self, table: EditableTable, row: int) -> tuple[int, int]:
        return (id(table), row)

    def _schedule_gender_split(self, table: EditableTable, row: int) -> None:
        self._cancel_gender_split(table, row)
        timer = QTimer(self)  # type: ignore[arg-type]
        timer.setSingleShot(True)
        timer.setInterval(self.GENDER_SPLIT_DELAY_MS)
        timer.timeout.connect(lambda: self._apply_gender_split(table, row))
        self._gender_split_timers[self._timer_key(table, row)] = timer
        timer.start()

    def _cancel_gender_split(self, table: EditableTable, row: int) -> None:
        timer = self._gender_split_timers.pop(self._timer_key(table, row), None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def _row_extra_flag(self, table: EditableTable, row: int, flag: str) -> bool:
        store = getattr(getattr(table, "_register_model", None), "store", None)
        if store is not None and row < len(store.row_extra):
            return bool(store.row_extra[row].get(flag))
        return False

    def _apply_gender_split(self, table: EditableTable, row: int) -> None:
        self._gender_split_timers.pop(self._timer_key(table, row), None)
        if self._row_extra_flag(table, row, OVERRIDE_PARTICIPANTI_GENDER):
            return

        rows = table.get_data_rows()
        if row < 0 or row >= len(rows):
            return

        row_dict = dict(rows[row])
        total = int(row_dict.get(self.PARTICIPANTI_TOTAL_KEY) or 0)
        if total <= 0:
            return

        if not apply_participant_gender_split(
            row_dict,
            total_key=self.PARTICIPANTI_TOTAL_KEY,
            m_key=self.PARTICIPANTI_M_KEY,
            f_key=self.PARTICIPANTI_F_KEY,
        ):
            return

        table.set_data_cell_silent(
            row, self.PARTICIPANTI_M_KEY, int(row_dict[self.PARTICIPANTI_M_KEY])
        )
        table.set_data_cell_silent(
            row, self.PARTICIPANTI_F_KEY, int(row_dict[self.PARTICIPANTI_F_KEY])
        )
        self._dirty = True
        self._recompute_visible_totals()
        m = int(row_dict[self.PARTICIPANTI_M_KEY])
        f = int(row_dict[self.PARTICIPANTI_F_KEY])
        self.main_window.statusBar().showMessage(
            f"Masculin/Feminin completat automat ({m} + {f} = {total}). "
            "Editați manual coloanele dacă doriți alte valori.",
            6000,
        )
