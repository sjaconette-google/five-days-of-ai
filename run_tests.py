"""Test runner script for executing unit tests and evaluation harness natively."""

import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tests.test_schemas import (
    test_gmail_message_parsing,
    test_strict_schema_extra_fields_forbidden,
    test_triage_tool_contract_validation,
    test_capacity_plan_validation,
    test_codebase_type_annotations_completeness,
)

from tests.test_capacity import (
    test_capacity_matching_low_fatigue,
    test_capacity_matching_high_fatigue_scaling,
    test_planning_agent_chronotype_alignment,
)
from tests.test_agents import (
    test_adk_router_triage_delegation,
    test_adk_router_planning_delegation,
    test_adk_history_compaction,
    test_human_confirmation_gate_security,
)
from tests.test_eval_harness import test_rubric_evaluation_harness_score_pass


def main():
    print("=" * 60)
    print("RUNNING GTD & WORKLOAD FOCUS AGENT TEST SUITE")
    print("=" * 60)


    tests = [
        ("test_gmail_message_parsing", test_gmail_message_parsing),
        ("test_strict_schema_extra_fields_forbidden", test_strict_schema_extra_fields_forbidden),
        ("test_triage_tool_contract_validation", test_triage_tool_contract_validation),
        ("test_capacity_plan_validation", test_capacity_plan_validation),
        ("test_codebase_type_annotations_completeness", test_codebase_type_annotations_completeness),

        ("test_capacity_matching_low_fatigue", test_capacity_matching_low_fatigue),
        ("test_capacity_matching_high_fatigue_scaling", test_capacity_matching_high_fatigue_scaling),
        ("test_planning_agent_chronotype_alignment", test_planning_agent_chronotype_alignment),
        ("test_adk_router_triage_delegation", test_adk_router_triage_delegation),
        ("test_adk_router_planning_delegation", test_adk_router_planning_delegation),
        ("test_adk_history_compaction", test_adk_history_compaction),
        ("test_human_confirmation_gate_security", test_human_confirmation_gate_security),
        ("test_rubric_evaluation_harness_score_pass", test_rubric_evaluation_harness_score_pass),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            print(f" [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f" [FAIL] {name}: {e}")
            failed += 1

    print("=" * 60)
    print(f"RESULTS: {passed} PASSED, {failed} FAILED out of {len(tests)} tests.")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
