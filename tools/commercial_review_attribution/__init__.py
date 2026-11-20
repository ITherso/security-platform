"""Standalone demo-only review attribution step; no production entry point.

Records a declared reviewer reference and review time on a finalized Phase19
desk overlay. It never authenticates a person, verifies a review or authorizes
delivery or release.
"""

MANIFEST_CONTRACT = "termivar-review-attribution-manifest/v1"
OVERLAY_NAME = "decision-overlay.json"
MANIFEST_NAME = "attribution-manifest.json"
