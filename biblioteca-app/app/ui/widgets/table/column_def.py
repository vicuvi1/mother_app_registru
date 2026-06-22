"""Definiție coloană tabel registru."""

from dataclasses import dataclass


@dataclass
class ColumnDef:
    key: str
    col_type: str = "int"  # int, text, date, bool, responsabil, scope_local, ...
    editable: bool = True
    computed_from: list[str] | None = None
    group: str | None = None
    count_in_total: bool = False

    def counts_checked_in_total(self) -> bool:
        return self.count_in_total and (
            self.col_type == "bool" or self.col_type.startswith("scope_")
        )

    def uses_cell_widget(self) -> bool:
        return self.col_type in (
            "bool",
            "responsabil",
            "preset_text",
            "inline_text",
        ) or self.col_type.startswith("scope_")
