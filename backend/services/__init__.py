from backend.services.intent_service import (
    has_science_domain_signatures,
    understand_response_content,
    infer_domain_from_content,
    get_domain_reference,
    discover_methodology,
)
from backend.services.response_aggregator import (
    score_response,
    compare_and_select,
    self_verify,
    cross_source_merge,
    list_divergences,
)