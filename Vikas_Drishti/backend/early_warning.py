"""Rule-based environmental early-warning assessment."""
def assess_early_warning(rainfall_mm, drainage_condition, flood_history, heat_index_c):
    score, reasons = 0, []
    if rainfall_mm >= 100:
        score += 40; reasons.append("very heavy rainfall forecast")
    elif rainfall_mm >= 64:
        score += 25; reasons.append("heavy rainfall forecast")
    elif rainfall_mm >= 35:
        score += 10; reasons.append("moderate rainfall forecast")
    if drainage_condition <= 25:
        score += 30; reasons.append("very poor drainage")
    elif drainage_condition <= 50:
        score += 20; reasons.append("poor drainage")
    if flood_history:
        score += 15; reasons.append("previous flooding reported")
    if heat_index_c >= 45:
        score += 25; reasons.append("extreme heat index")
    elif heat_index_c >= 40:
        score += 15; reasons.append("high heat index")
    score = min(score, 100)
    level = "High Alert" if score >= 60 else "Watch" if score >= 30 else "Normal"
    action = ("Notify officers, inspect vulnerable households and clear drains immediately." if level == "High Alert"
              else "Monitor forecasts, verify drainage and prepare response teams." if level == "Watch"
              else "Continue routine monitoring and preparedness.")
    return {"Alert_Score": score, "Alert_Level": level,
            "Reasons": reasons or ["No threshold-based environmental warning detected"],
            "Recommended_Action": action}
