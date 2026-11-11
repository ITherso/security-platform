"""Independent demo-only offline scope planning; no runtime integration."""

PROPOSAL_CONTRACT = "termivar-assessment-scope-proposal/v1"
PLAN_CONTRACT = "termivar-assessment-plan-proposal/v1"
DEMO_LABEL = "DEMONSTRATION ONLY — NO TARGET ASSESSED — NO EXECUTION AUTHORIZED"
MAX_PROPOSAL_BYTES = 128 * 1024
MAX_SAFE_INTEGER = (1 << 53) - 1
REVIEW_REQUIREMENTS = (
    "scope_owner", "authorization", "data_handling", "human_review",
    "runtime_qualification",
)
