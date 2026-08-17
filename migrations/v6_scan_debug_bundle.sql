-- Migration: v6_scan_debug_bundle
-- Description: Store the latest sandbox debug bundle reference for each scan.

ALTER TABLE scans
    ADD COLUMN IF NOT EXISTS debug_bundle TEXT;
