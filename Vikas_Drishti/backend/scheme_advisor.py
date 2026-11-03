"""Explainable scheme matching for urban development needs. Not an eligibility decision."""

SCHEMES = {
    "PMAY-U 2.0": {
        "focus": "Affordable housing, in-situ improvement/redevelopment of eligible tenable slums",
        "needs": {"Housing": 0.45},
        "detail": "Potential pathways include BLC for eligible households and AHP for eligible redevelopment / in-situ improvement proposals. Household, land, tenure, state participation and ULB appraisal conditions apply.",
        "url": "https://pmay-urban.gov.in/",
        "authority": "Ministry of Housing and Urban Affairs (MoHUA) / State / ULB",
    },
    "AMRUT 2.0": {
        "focus": "Water supply, sewerage/septage management and water-body rejuvenation",
        "needs": {"Water": 0.45, "Drainage": 0.45},
        "detail": "Recommend the relevant water/sewerage proposal for appraisal through the State and Urban Local Body; city action-plan and mission guidelines determine coverage.",
        "url": "https://amrut.gov.in/",
        "authority": "MoHUA / State / ULB",
    },
    "Swachh Bharat Mission–Urban 2.0": {
        "focus": "Sanitation, public/community toilets, solid-waste management and wastewater management",
        "needs": {"Sanitation": 0.45, "Drainage": 0.45},
        "detail": "Use for a sanitation and waste-management intervention proposal through the ULB, subject to current mission components and State/ULB plans.",
        "url": "https://swachhbharaturban.gov.in/",
        "authority": "MoHUA / State / ULB",
    },
    "DAY-NULM / urban livelihoods convergence": {
        "focus": "Urban poor livelihoods, skills, self-employment and community institutions",
        "needs": {},
        "needs_high": {"Livelihood_Gap": 0.50, "Unemployment_Rate": 0.50},
        "detail": "Potential convergence where livelihood, skills or self-employment needs are documented. Confirm the currently applicable state/ULB programme and operational guidelines before referral.",
        "url": "https://nulm.gov.in/",
        "authority": "State Urban Livelihoods Mission / ULB",
    },
}


def recommend_schemes(row, limit=4):
    """Return ranked scheme matches based on low service scores (0..1 or 0..100)."""
    results = []
    for name, item in SCHEMES.items():
        evidence = []
        for indicator, threshold in item.get("needs", {}).items():
            if indicator in row.index:
                value = float(row[indicator])
                if value > 1:
                    value /= 100.0
                if value <= threshold:
                    evidence.append(f"{indicator} service score is {value * 100:.0f}/100")
        for indicator, threshold in item.get("needs_high", {}).items():
            if indicator in row.index:
                value = float(row[indicator])
                if value > 1:
                    value /= 100.0
                if value >= threshold:
                    evidence.append(f"{indicator} indicates a substantial livelihoods gap ({value * 100:.0f}/100)")
        if evidence:
            results.append({"scheme": name, "focus": item["focus"], "evidence": evidence,
                            "detail": item["detail"], "url": item["url"],
                            "authority": item["authority"], "match_count": len(evidence)})
    return sorted(results, key=lambda x: x["match_count"], reverse=True)[:limit]
