from pathlib import Path


def test_base_schema_creates_scan_debug_bundle_column():
    migration = Path("alembic/versions/20260525_0001_schema_v2_2.py").read_text()

    assert 'sa.Column("debug_bundle", sa.Text(), nullable=True)' in migration


def test_base_schema_creates_scan_crew_report_columns():
    migration = Path("alembic/versions/20260525_0001_schema_v2_2.py").read_text()

    assert 'sa.Column("crew_report_json", sa.Text(), nullable=True)' in migration
    assert 'sa.Column("crew_report_markdown", sa.Text(), nullable=True)' in migration


def test_scan_proto_exposes_crewai_fields_on_get_scan_status():
    proto = Path("src/aegis/v2/scan.proto").read_text()

    assert "string crew_report_json = 8;" in proto
    assert "string crew_report_markdown = 9;" in proto
