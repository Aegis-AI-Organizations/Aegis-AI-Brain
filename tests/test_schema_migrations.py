from pathlib import Path


def test_base_schema_creates_scan_debug_bundle_column():
    migration = Path("alembic/versions/20260525_0001_schema_v2_2.py").read_text()

    assert 'sa.Column("debug_bundle", sa.Text(), nullable=True)' in migration
