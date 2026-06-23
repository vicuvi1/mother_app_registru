"""Teste sincronizare Partea III → Partea IV."""

from core.part_sync import apply_part04_totals, part03_has_imprumut_data

CZU = ["czu_0_generalitati", "czu_1_filozofie"]


def test_part03_has_imprumut_data_detects_section():
    assert part03_has_imprumut_data({"consultare_pe_loc": 2})
    assert not part03_has_imprumut_data({"carti": 5})
    assert not part03_has_imprumut_data(None)


def test_apply_part04_totals_from_part03():
    rows = [{"data": "01.03", "czu_0_generalitati": 1, "czu_1_filozofie": 2}]
    p3 = {"01.03": {"total_imprumuturi": 10, "consultare_pe_loc": 4}}
    apply_part04_totals(rows, p3, CZU)
    assert rows[0]["total_imprumuturi"] == 10
    assert rows[0]["_sync_total_from_part03"] is True


def test_apply_part04_totals_sums_czu_when_part03_empty():
    rows = [{"data": "02.03", "czu_0_generalitati": 3, "czu_1_filozofie": 4}]
    apply_part04_totals(rows, {}, CZU)
    assert rows[0]["total_imprumuturi"] == 7
    assert rows[0]["_sync_total_from_part03"] is False
