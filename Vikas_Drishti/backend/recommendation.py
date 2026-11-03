"""Transparent, explainable rule-based development recommendations."""

def generate_recommendation(row):
    recommendations = []
    checks = [
        ("Sanitation", "improve sanitation facilities, public toilets and waste collection"),
        ("Water", "repair water-supply lines and improve access to safe drinking water"),
        ("Housing", "prioritize safer housing repairs and structural-risk mitigation"),
        ("Roads", "repair internal roads, improve walkability and restore road access"),
        ("Drainage", "construct or desilt storm-water drains and improve wastewater flow"),
        ("Healthcare", "organize health camps and improve access to nearby healthcare"),
        ("Electricity", "improve safe electricity connections and street lighting"),
    ]
    for column, action in checks:
        if column in row.index and float(row[column]) < 0.4:
            recommendations.append(action)
    if "Crime" in row.index and float(row["Crime"]) > 0.6:
        recommendations.append("improve street lighting, community safety and coordinated patrolling")
    if not recommendations:
        return "Continue routine maintenance and periodic monitoring; no severe service gap was identified."
    score = float(row.get("Priority_Score", 0))
    level = "Immediate intervention" if score >= 80 else "High-priority intervention" if score >= 60 else "Planned improvement"
    return level + ": " + "; ".join(recommendations) + "."
