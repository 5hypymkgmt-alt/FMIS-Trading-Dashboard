
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

