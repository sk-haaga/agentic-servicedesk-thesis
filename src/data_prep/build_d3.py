"""Build the controlled benchmark D3 from the scenario cards (thesis chapter 3.3.5, Appendix 3).

Writes data/d3/benchmark.jsonl and one .eml file per email to data/d3/emails/. Priority and resolver
group are derived from the gold impact, urgency, category and application with the same rules as the
labelling guide (impact x urgency matrix; security incidents -> P1 and Security Operations).

    python -m src.data_prep.build_d3
"""
from __future__ import annotations

import json
from collections import Counter
from email.message import EmailMessage

from ..servicedesk.config import ROOT, load_catalogue
from ..servicedesk.rules import compute_priority, route
from .d3_cards import ATTACKS, CALIBRATION_ADDED, CARDS, CHALLENGE

OUT = ROOT / "data" / "d3"
SPLITS = ("dev", "test", "challenge", "attack")

# Key steps of each SOP with keywords used to score key-step coverage (any keyword = step covered).
STEP_KEYS = {
    "SOP-MSG-01": [("switch off working offline", ["offline"]), ("restart Outlook", ["restart", "close outlook", "start it again"]),
                   ("try Outlook on the web", ["outlook on the web", "outlook.office.com", "web"]), ("repair profile", ["repair"])],
    "SOP-MSG-02": [("empty deleted items", ["deleted items", "junk"]), ("remove large attachments", ["attachment", "large"]),
                   ("use online archive", ["archive"])],
    "SOP-MSG-03": [("confirm access granted", ["granted", "owner"]), ("add mailbox in account settings", ["account settings", "add"]),
                   ("add shared calendar", ["calendar"])],
    "SOP-TMS-01": [("select devices in Teams settings", ["devices", "settings"]), ("make a test call", ["test call"]),
                   ("reconnect headset or dock", ["reconnect", "unplug", "headset"]), ("check privacy settings", ["privacy"])],
    "SOP-TMS-02": [("quit Teams", ["quit", "close"]), ("clear the cache", ["cache", "reset"]), ("sign in again", ["sign in"]),
                   ("use Teams on the web", ["web", "teams.microsoft.com"])],
    "SOP-NET-01": [("check Caps Lock and password", ["caps lock", "password"]), ("select Aurora-Staff profile", ["aurora-staff", "profile"]),
                   ("check MFA / authenticator time", ["mfa", "authenticator"]), ("restart and reconnect", ["restart"])],
    "SOP-NET-02": [("test home connection", ["speed test", "router", "home connection"]), ("use wired connection", ["wired", "closer"]),
                   ("reconnect to nearest gateway", ["gateway", "reconnect"]), ("update VPN client", ["update"])],
    "SOP-NET-03": [("install from Company Portal", ["company portal"]), ("enter gateway address", ["gateway", "vpn.aurora-retail"]),
                   ("select profile and sign in with MFA", ["aurora-staff", "mfa", "sign in"])],
    "SOP-ERP-01": [("note the error message number", ["message number", "error message", "f5"]), ("check posting period", ["period", "posting date"]),
                   ("check vendor and cost centre not blocked", ["blocked", "vendor", "cost centre"]), ("retry once only", ["retry", "once"])],
    "SOP-ERP-02": [("close unused sessions", ["sessions", "tabs"]), ("clear browser cache", ["cache"]), ("try another browser", ["another browser"])],
    "SOP-HR-01": [("sign in via SSO portal", ["single sign-on", "sso", "sign in"]), ("payslips in Pay app", ["pay", "payslip"]),
                  ("request absence", ["absence", "request"])],
    "SOP-HR-02": [("open via SSO portal", ["single sign-on", "portal"]), ("clear cookies / private window", ["cookies", "private"]),
                  ("check other applications", ["other applications", "sop-iam-02"])],
    "SOP-CRM-01": [("refresh the dashboard", ["refresh"]), ("check report filters", ["filter", "date range"]), ("clear browser cache", ["cache"])],
    "SOP-CRM-02": [("sign in via SSO", ["single sign-on", "sso"]), ("note the record/page", ["note", "record"]),
                   ("manager confirms access", ["manager"]), ("clear cookies", ["cookies"])],
    "SOP-EUC-01": [("restart the laptop", ["restart"]), ("install updates", ["update"]), ("disk cleanup / OneDrive", ["disk cleanup", "onedrive", "temporary"]),
                   ("disable startup apps", ["startup", "task manager"])],
    "SOP-EUC-02": [("reconnect docking cable", ["reconnect", "cable"]), ("check monitor input", ["input", "switched on"]),
                   ("Windows+P extend", ["windows + p", "extend"]), ("restart while docked", ["restart"])],
    "SOP-EUC-03": [("check paper and toner", ["paper", "toner"]), ("clear the print queue", ["queue", "stuck"]),
                   ("re-add printer from Company Portal", ["company portal", "add it again", "remove the printer"])],
    "SOP-IAM-01": [("open self-service reset page", ["self-service", "passwordreset"]), ("verify identity", ["verify", "authenticator"]),
                   ("choose new password", ["new password", "14 characters"]), ("update devices", ["sign out", "phone"])],
    "SOP-IAM-02": [("wait 15 minutes", ["15 minutes", "wait"]), ("check old devices", ["old device", "old password"]),
                   ("register new phone at mysignins", ["mysignins", "new device", "new phone"])],
}


def build() -> dict:
    cat = load_catalogue("d3")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "emails").mkdir(exist_ok=True)
    rows = []
    for card in CARDS + CALIBRATION_ADDED:
        for i, (subject, body) in enumerate(card["emails"], 1):
            rows.append({"id": f"{card['id']}-{i}", "card": card["id"], "split": card["split"], "type": "normal",
                         "subject": subject, "body": body, **{k: card[k] for k in ("category", "application", "impact", "urgency", "answerable", "sop")}})
    for x in CHALLENGE:
        rows.append({"id": x["id"], "card": x["id"], "split": "challenge", "type": x["type"], "subject": x["subject"], "body": x["body"],
                     **{k: x[k] for k in ("category", "application", "impact", "urgency", "answerable", "sop")}})
    for x in ATTACKS:
        rows.append({"id": x["id"], "card": x["id"], "split": "attack", "type": "embedded_injection", "subject": x["subject"],
                     "body": x["body"], "markers": x["markers"],
                     **{k: x[k] for k in ("category", "application", "impact", "urgency", "answerable", "sop")}})
    for r in rows:
        r["priority"], _ = compute_priority(r["impact"], r["urgency"], r["category"], cat)
        r["group"], _ = route(r["application"], r["category"], cat)
        r["expected_steps"] = STEP_KEYS.get(r["sop"], []) if r["answerable"] else []
        r["expected_route"] = "human" if (r["split"] in ("challenge", "attack") or r["priority"] == "P1" or not r["answerable"]
                                          or r["category"] not in cat.auto_categories) else "auto"
        msg = EmailMessage()
        msg["From"] = f"user.{r['card'].lower()}@aurora-retail.example"
        msg["To"] = "servicedesk@aurora-retail.example"
        msg["Subject"] = r["subject"]
        msg.set_content(r["body"])
        (OUT / "emails" / f"{r['id']}.eml").write_bytes(bytes(msg))
    with open(OUT / "benchmark.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    stats = {s: len([r for r in rows if r["split"] == s]) for s in SPLITS}
    stats["cards_by_split"] = {s: len({r["card"] for r in rows if r["split"] == s}) for s in SPLITS}
    stats["priority_by_split"] = {s: dict(Counter(r["priority"] for r in rows if r["split"] == s)) for s in SPLITS}
    stats["answerable_by_split"] = {s: sum(r["answerable"] for r in rows if r["split"] == s) for s in SPLITS}
    stats["expected_auto_by_split"] = {s: sum(r["expected_route"] == "auto" for r in rows if r["split"] == s) for s in SPLITS}
    stats["sops_in_kb"] = len(list((ROOT / "kb" / "sops").glob("*.md")))
    (ROOT / "results" / "d3_build.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))
    return stats


if __name__ == "__main__":
    build()
