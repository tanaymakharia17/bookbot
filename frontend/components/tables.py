import html


def _totals(entry: dict) -> tuple[float, float, bool]:
    lines = entry.get("lines", [])
    debit = entry.get("total_debits")
    credit = entry.get("total_credits")
    if debit is None:
        debit = sum(l["amount"] for l in lines if l["entry_type"] == "DEBIT")
    if credit is None:
        credit = sum(l["amount"] for l in lines if l["entry_type"] == "CREDIT")
    balanced = entry.get("balanced")
    if balanced is None:
        balanced = abs(debit - credit) < 0.001
    return round(debit, 2), round(credit, 2), balanced


def _chip(text: str, kind: str = "") -> str:
    css = "bb-chip" + (f" bb-chip-{kind}" if kind else "")
    return f"<span class='{css}'>{html.escape(str(text))}</span>"


def line_items_html(items: list[dict], threshold: float) -> str:
    if not items:
        return "<div class='bb-doc-text'>No line items yet.</div>"

    rows = []
    for i, li in enumerate(items, start=1):
        personal = li.get("personal")
        capex = (not personal) and li["amount"] >= threshold
        row_class = " class='bb-row-personal'" if personal else ""

        if personal:
            category = _chip("Personal · excluded", "personal")
        elif capex:
            category = _chip(li["category"], "capex")
        else:
            category = _chip(li["category"])

        rows.append(
            f"<tr{row_class}>"
            f"<td class='bb-num'>{i}</td>"
            f"<td>{html.escape(li['description'])}</td>"
            f"<td class='bb-num'>{li['qty']}</td>"
            f"<td class='bb-num'>${li['unit_price']:,.2f}</td>"
            f"<td class='bb-num bb-strong'>${li['amount']:,.2f}</td>"
            f"<td>{category}</td>"
            "</tr>"
        )

    return (
        "<div class='bb-table-scroll'>"
        "<table class='bb-table'><thead><tr>"
        "<th>#</th><th>Description</th><th class='bb-num'>Qty</th>"
        "<th class='bb-num'>Unit price</th><th class='bb-num'>Amount</th><th>Category</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        "</div>"
    )


def journal_html(entry: dict) -> str:
    debit_total, credit_total, _ = _totals(entry)
    rows = []
    for line in entry["lines"]:
        debit = f"${line['amount']:,.2f}" if line["entry_type"] == "DEBIT" else "—"
        credit = f"${line['amount']:,.2f}" if line["entry_type"] == "CREDIT" else "—"
        rows.append(
            "<tr>"
            f"<td><span class='bb-strong'>{html.escape(line['account_code'])}</span> "
            f"{html.escape(line['account_name'])}</td>"
            f"<td>{html.escape(line['description'])}</td>"
            f"<td class='bb-num'>{debit}</td>"
            f"<td class='bb-num'>{credit}</td>"
            "</tr>"
        )

    rows.append(
        "<tr class='bb-row-total'>"
        "<td>Totals</td><td></td>"
        f"<td class='bb-num'>${debit_total:,.2f}</td>"
        f"<td class='bb-num'>${credit_total:,.2f}</td>"
        "</tr>"
    )

    return (
        "<div class='bb-table-scroll'>"
        "<table class='bb-table'><thead><tr>"
        "<th>Account</th><th>Description</th>"
        "<th class='bb-num'>Debit</th><th class='bb-num'>Credit</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        "</div>"
    )


def balance_banner(entry: dict) -> str:
    debit_total, credit_total, balanced = _totals(entry)
    if balanced:
        return (
            "<div class='bb-balance ok'>⚖️ Balanced — debits = credits = "
            f"${debit_total:,.2f}</div>"
        )
    return "<div class='bb-balance bad'>⚠️ Unbalanced entry</div>"