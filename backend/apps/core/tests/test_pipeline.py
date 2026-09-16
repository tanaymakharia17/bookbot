from decimal import Decimal

from django.test import SimpleTestCase

from apps.core.pipeline import LedgerPipeline, LedgerState
from apps.core.pipeline.rules import (
    CapExThresholdRule,
    DoubleEntryBalanceRule,
    JournalBuilderRule,
    PersonalExpenseRule,
)
from apps.core.pipeline.state import CREDIT, DEBIT, LedgerEntryDraft, LedgerLineItem


def run_pipeline(lines, payment="Company Credit Card"):
    state = LedgerState(
        submission_id="s",
        client_id="c",
        vendor="Apple Store",
        payment_method=payment,
        lines=lines,
    )
    return LedgerPipeline([
        PersonalExpenseRule(),
        CapExThresholdRule(),
        JournalBuilderRule(),
        DoubleEntryBalanceRule(),
    ]).process(state)


class PipelineTests(SimpleTestCase):
    def test_capitalizes_item_over_threshold(self):
        state = run_pipeline([LedgerLineItem("MacBook Pro", Decimal("2899.00"), "IT Equipment")])
        debit = next(e for e in state.posted_entries if e.entry_type == DEBIT)
        self.assertEqual(debit.account_code, "1500")
        self.assertEqual(debit.account_name, "Fixed Assets")

    def test_excludes_personal_from_reimbursement(self):
        state = run_pipeline([
            LedgerLineItem("Supplies", Decimal("100.00"), "Office Supplies"),
            LedgerLineItem("Vacuum", Decimal("350.00"), "Uncategorized", personal=True),
        ])
        self.assertEqual(state.total_reimbursement_payable, Decimal("100.00"))
        debits = [e for e in state.posted_entries if e.entry_type == DEBIT]
        self.assertEqual(len(debits), 1)

    def test_journal_is_balanced(self):
        state = run_pipeline([
            LedgerLineItem("Display", Decimal("1599.00"), "IT Equipment"),
            LedgerLineItem("Paper", Decimal("89.00"), "Office Supplies"),
        ])
        debits = sum(e.amount for e in state.posted_entries if e.entry_type == DEBIT)
        credits = sum(e.amount for e in state.posted_entries if e.entry_type == CREDIT)
        self.assertEqual(debits, credits)

    def test_double_entry_rule_raises_when_unbalanced(self):
        state = LedgerState(
            submission_id="s",
            client_id="c",
            posted_entries=[
                LedgerEntryDraft("6050", "IT", DEBIT, Decimal("10.00")),
                LedgerEntryDraft("2010", "Card", CREDIT, Decimal("9.00")),
            ],
        )
        with self.assertRaises(ValueError):
            DoubleEntryBalanceRule().execute(state)