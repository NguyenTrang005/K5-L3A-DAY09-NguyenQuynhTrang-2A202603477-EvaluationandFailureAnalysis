import pytest

pytestmark = pytest.mark.student


@pytest.fixture(scope="module")
def c014_cases():
    from lab9.trace_case import investigate

    return {shape: investigate(shape, "C-014", 11)
            for shape in ("seeded_regression", "fixed")}


def assert_c014_refund_contract(case):
    trial, label = case["trial"], case["label"]
    assert trial["result"]["status"] != "error", trial["lab8_reason"]
    assert trial["events"], "Trace must be available"
    assert trial["result"]["proposal_amount"] == label["proposal_amount"], "Full quote must reach host"
    assert trial["snapshot"]["refund_vnd"] == label["refund_vnd"], "Historical refund must be deducted once"
    assert trial["snapshot"]["refund_count"] == label["refund_count"]
    assert trial["unexpected_rows"] == 0
    assert trial["lab8_pass"], trial["lab8_reason"]


def test_lab9_c014_fixed_preserves_full_quote(c014_cases):
    case = c014_cases["fixed"]
    assert case["label"]["proposal_amount"] == 150000
    assert case["label"]["refund_vnd"] == 120000
    assert_c014_refund_contract(case)


def test_lab9_c014_detects_double_deduction(c014_cases):
    case = c014_cases["seeded_regression"]
    trial = case["trial"]
    assert trial["result"]["status"] == "resolved"
    assert trial["result"]["proposal_amount"] == 120000
    assert trial["snapshot"]["refund_vnd"] == 90000
    assert not trial["lab8_pass"]
    assert trial["lab8_reason"] == "proposal_mismatch"
    assert trial["events"][4]["kind"] == "proposal"
    assert trial["events"][4]["payload"]["amount_vnd"] == 120000
    with pytest.raises(AssertionError, match="Full quote must reach host"):
        assert_c014_refund_contract(case)


@pytest.mark.parametrize("shape,expected", [("fixed", True), ("seeded_regression", False)])
def test_lab9_c014_reply_grader_matches_actual_ledger(c014_cases, shape, expected):
    from pydantic_evals.evaluators import EvaluatorContext
    from lab9.graders import ReplyAmountCorrect

    case = c014_cases[shape]
    context = EvaluatorContext(name="C-014@11", inputs={}, metadata=None,
                               expected_output=case["label"], output=case["trial"],
                               duration=0.0, _span_tree=None, attributes={}, metrics={})
    assert ReplyAmountCorrect().evaluate(context).value is expected
