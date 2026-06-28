"""Consistență registry părți — tab Copii/Adulți vs. model DB."""

from core.part_models import get_part_model
from core.parts_registry import PART_ENTRIES


def test_has_copii_adulti_matches_model_category_column():
    for entry in PART_ENTRIES:
        part_id = entry["part_id"]
        model = get_part_model(part_id)
        assert model is not None, part_id
        expects_tabs = hasattr(model, "categorie_varsta")
        assert entry["has_copii_adulti"] == expects_tabs, (
            f"{part_id}: registry has_copii_adulti={entry['has_copii_adulti']}, "
            f"model has categorie_varsta={expects_tabs}"
        )
