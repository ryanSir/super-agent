---
name: patent-legal-status
description: Patent Legal Status Query - Query the current legal status of a patent (Active/Lapsed/Pending, etc.). Applicable to infringement risk analysis, FTO investigations, patent valuation, patent due diligence, patent portfolio management, and more.
---

# Patent Legal Status Query Skill

Query the current legal status of a patent (Active/Lapsed/Pending, etc.) for infringement risk analysis, FTO investigations, patent valuation, and other scenarios.

Core principle: After finding similar patents, you must first check the legal status to confirm validity before assessing risk. Lapsed patents do not constitute infringement; patents under examination carry lower risk (not yet granted); active patents require detailed analysis.

## Script Usage

```bash
# Query legal status of a single patent
python ${CLAUDE_SKILL_DIR}/scripts/legal_status.py "CN110245964A"

# Query using patent ID
python ${CLAUDE_SKILL_DIR}/scripts/legal_status.py "640cd059-3615-4bc6-bec2-f7bd57209733"
```

### Parameters

- `<Patent ID or Publication Number>` - Patent ID (PatSnap UUID) or patent publication number, single patent only
- `--base-url <url>` - API base URL

Note: The script only supports single patent queries. For batch queries, the Agent initiates multiple independent calls.

## Output Format

```json
{
    "status": true,
    "render_type": "patent-legal-status",
    "data": {
        "LEGAL_STATUS": {
            "INPADOC_FAMILY_STATUS": "Granted",
            "SIMPLE_FAMILY_STATUS": "Granted",
            "ORIGINAL_LEGAL_STATUS": [
                "Granted"
            ],
            "LEGAL_STATUS_DATE": "15 Oct 2024",
            "PATSNAP_FAMILY_STATUS": "Active"
        },
        "LEGAL": {},
        "LEGAL_STATUS_DATE": "15 Oct 2024",
        "LEGAL_UPC": {}
    }
```

## Legal Status Interpretation

| Status | Meaning | Infringement Risk | Recommendation |
|--------|---------|-------------------|----------------|
| Active | Patent is within its protection period | High | Detailed claim analysis required |
| Pending | Patent application not yet granted | Low | Monitor examination progress |
| Lapsed | Patent rights have been terminated | None | Free to practice, but watch for improvement patents |
| Expired | Protection period ended (20 years) | None | Free to practice |
| Withdrawn | Applicant voluntarily withdrew | None | Free to practice |
| Rejected | Rejected during examination | None | Free to practice |

## Workflow Examples

### Infringement Risk Analysis (Cross-Skill Collaboration)

```bash
# Step 1: Find similar patents (patent-similar)
python ${PATENT_SIMILAR_DIR}/scripts/similar_search.py "target patent number"

# Step 2: Query legal status for each similar patent
python ${CLAUDE_SKILL_DIR}/scripts/legal_status.py "similar patent publication number"

# Step 3: Query details for active patents (patent-info)
python ${PATENT_INFO_DIR}/scripts/patent_info.py "active patent number"
```

The Agent extracts patent numbers from each step's JSON results and initiates the next independent call. After filtering active patents, it proceeds with claim analysis.

### FTO Investigation

```bash
# Step 1: Search related patents (patent-search)
python ${PATENT_SEARCH_DIR}/scripts/patent_search.py "search criteria"

# Step 2: Query legal status for each patent, filter active ones
python ${CLAUDE_SKILL_DIR}/scripts/legal_status.py "patent publication number"

# Step 3: Perform detailed claim analysis on active patents
```

The Agent iterates through search results, calls legal status queries individually, and aggregates the filtered results.

## Important Notes

- Legal status changes over time; always re-query the latest status before infringement analysis
- Patent family members may have different legal statuses in different countries (CN Active ≠ US Active); query each target market separately
- Lapsed patents are free to practice, but check whether improvement patents are still active
- Citation analysis and legal status conclusions are for reference only; consult a professional attorney for important decisions

## Related Skills

- `patent-search` - Standard search
- `patent-similar` - Similar patent search
- `patent-info` - Patent detail query
- `patent-citation-analysis` - Citation analysis
- `patent-family` - Patent family query
