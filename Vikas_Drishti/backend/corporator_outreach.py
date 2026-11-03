"""Ward representative lookup and optional email notification delivery."""
from __future__ import annotations
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
import pandas as pd

REQUIRED = ["Area", "Ward", "Corporator_Name", "Email", "Phone", "Municipal_Body"]
LOG_PATH = Path("data/corporator_notification_log.csv")


def load_directory(uploaded_file=None):
    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
    elif Path("data/corporator_directory.csv").exists():
        data = pd.read_csv("data/corporator_directory.csv")
    else:
        return pd.DataFrame(columns=REQUIRED)
    for col in REQUIRED:
        if col not in data.columns:
            data[col] = ""
    return data[REQUIRED].fillna("")


def find_representative(directory, area):
    if directory.empty:
        return None
    match = directory[directory["Area"].astype(str).str.strip().str.casefold() == str(area).strip().casefold()]
    return None if match.empty else match.iloc[0].to_dict()


def notification_text(area, row, representative, schemes):
    name = representative.get("Corporator_Name") or "Elected Ward Representative"
    ward = representative.get("Ward") or "Not specified"
    scheme_text = ", ".join(x["scheme"] for x in schemes) or "To be assessed by the ULB"
    return (f"Dear {name},\n\nThis is an area-development situation report from Vikas Drishti.\n"
            f"Area: {area}\nWard: {ward}\nPopulation (dataset): {int(float(row.get('Population', 0))):,}\n"
            f"Priority score: {float(row.get('Priority_Score', 0)):.1f}/100\n"
            f"Risk level: {row.get('Risk_Level', 'Not assessed')}\n"
            f"Cluster: {row.get('Cluster_Label', row.get('Cluster', 'Not assigned'))}\n"
            f"Development needs: {row.get('Recommendation', 'Field assessment required')}\n"
            f"Potential scheme convergence: {scheme_text}\n\n"
            "Please arrange a ward-level verification and coordinate with the relevant municipal departments. "
            "The attached/linked assessment is a decision-support lead and should be validated through field inspection and official scheme eligibility checks.\n\n"
            "Regards,\nVikas Drishti – Urban Development Monitoring")


def send_email(recipient, subject, body):
    host = os.getenv("SMTP_HOST", "")
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM", user)
    if not all([host, user, password, sender, recipient]):
        return False, "Email is not configured. Add SMTP_HOST, SMTP_USER, SMTP_PASSWORD and SMTP_FROM environment variables. The draft can still be downloaded."
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = sender, recipient, subject
    msg.set_content(body)
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True, "Notification email sent successfully."
    except Exception as exc:
        return False, f"Email delivery failed: {exc}"


def log_notification(area, recipient, subject, status):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = pd.DataFrame([{"Timestamp": pd.Timestamp.now().isoformat(timespec="seconds"),
                           "Area": area, "Recipient": recipient, "Subject": subject, "Status": status}])
    entry.to_csv(LOG_PATH, mode="a", header=not LOG_PATH.exists(), index=False)
