
"""CFTC Commitment of Traders data collector for FMIS.

COT reports are published weekly, not in real time.
This module will remain separate from existing FMIS scoring.
"""

import requests
from datetime import datetime, timezone

CFTC_API_BASE = "https://publicreporting.cftc.gov/resource"

# Official CFTC public datasets
COT_DATASETS = {
    "disaggregated": "72hh-3qpy",
    "financial_futures": "gpe5-46if",
}

REQUEST_TIMEOUT = 30


def fetch_cot_data(dataset, market_code):
    """Retrieve the latest five COT reports for a futures market."""

    url = f"{CFTC_API_BASE}/{COT_DATASETS[dataset]}.json"

    params = {
        "$where": f"cftc_contract_market_code = '{market_code}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": 5,
    }

    response = requests.get(
        url,
        params=params,
        timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()

    return response.json()


def calculate_cot_positioning(reports):
    """Calculate net positioning and weekly change."""

    if len(reports) < 2:
        return {
            "status": "unavailable",
            "reason": "At least two weekly reports are required"
        }

    latest, previous = reports[0], reports[1]

    latest_long = int(latest["m_money_positions_long_all"])
    latest_short = int(latest["m_money_positions_short_all"])

    previous_long = int(previous["m_money_positions_long_all"])
    previous_short = int(previous["m_money_positions_short_all"])

    latest_net = latest_long - latest_short
    previous_net = previous_long - previous_short

    weekly_change = latest_net - previous_net

    if latest_net > 0:
        bias = "Net Long"
    elif latest_net < 0:
        bias = "Net Short"
    else:
        bias = "Neutral"

    return {
        "status": "ok",
        "report_date": latest["report_date_as_yyyy_mm_dd"][:10],
        "long": latest_long,
        "short": latest_short,
        "net": latest_net,
        "previous_net": previous_net,
        "weekly_change": weekly_change,
        "bias": bias
    }


if __name__ == "__main__":
    print("Fetching latest Gold COT reports...")

    reports = fetch_cot_data("disaggregated", "088691")
    result = calculate_cot_positioning(reports)

    print("Gold COT positioning:")
    print(result)


def calculate_financial_futures_positioning(reports):
    """Calculate Asset Manager and Leveraged Fund COT positioning."""

    if len(reports) < 2:
        return {
            "status": "unavailable",
            "reason": "At least two weekly reports are required"
        }

    latest, previous = reports[0], reports[1]

    def calculate_group(long_field, short_field):
        required = [
            long_field, short_field
        ]

        if any(
            latest.get(field) is None or previous.get(field) is None
            for field in required
        ):
            return {"status": "unavailable"}

        latest_long = int(latest[long_field])
        latest_short = int(latest[short_field])
        previous_long = int(previous[long_field])
        previous_short = int(previous[short_field])

        latest_net = latest_long - latest_short
        previous_net = previous_long - previous_short

        if latest_net > 0:
            bias = "Net Long"
        elif latest_net < 0:
            bias = "Net Short"
        else:
            bias = "Neutral"

        return {
            "status": "ok",
            "long": latest_long,
            "short": latest_short,
            "net": latest_net,
            "previous_net": previous_net,
            "weekly_change": latest_net - previous_net,
            "bias": bias
        }

    return {
        "status": "ok",
        "report_date": latest["report_date_as_yyyy_mm_dd"][:10],
        "asset_managers": calculate_group(
            "asset_mgr_positions_long",
            "asset_mgr_positions_short"
        ),
        "leveraged_funds": calculate_group(
            "lev_money_positions_long",
            "lev_money_positions_short"
        )
    }
