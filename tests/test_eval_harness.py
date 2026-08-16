from scripts.evaluate_agent import evaluate_queries


def test_eval_harness_all_cases_pass():
    result = evaluate_queries()
    assert result["total_cases"] == 20
    assert result["passed_cases"] == 20
    assert result["intent_accuracy"] == 1.0
    assert result["failures"] == []
