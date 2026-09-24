from pathlib import Path


def test_artifact_content_type_migration_expands_backfills_and_keeps_rollback_compatibility() -> (
    None
):
    migration = (
        (Path(__file__).parents[4] / "supabase/migrations/20260924150000_artifact_content_type.sql")
        .read_text(encoding="utf-8")
        .lower()
    )

    assert "add column if not exists content_type text" in migration
    assert "when lower(filename) like '%.csv' then 'text/csv'" in migration
    assert (
        "when lower(filename) like '%.xlsx' then 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'"
        in migration
    )
    assert "create or replace function public.reserve_artifact_v2" in migration
    assert "p_content_type text" in migration
    assert "expected_content_type is null" in migration
    assert "coalesce(current_row.content_type, expected_content_type)" in migration
    assert "insert into public.artifacts(" in migration
    assert "content_type" in migration
    assert "not null" not in migration
