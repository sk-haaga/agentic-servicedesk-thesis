---
id: SOP-ERP-01
title: "SAP: invoice posting fails"
applications: ['SAP S/4HANA Finance']
symptoms: "cannot post invoice, posting period closed, posting error, document not posted"
---
# SOP-ERP-01 SAP: invoice posting fails

Applies to: SAP S/4HANA Finance
Symptoms: cannot post invoice, posting period closed, posting error, document not posted

Steps for the user:
1. Read the full error message and note the message number (for example F5 201 'posting period not open').
2. Check that the posting date is in an open period; if the period is closed, change the posting date to the current period if this is allowed by the finance policy.
3. Check that the vendor and cost centre are not blocked.
4. Retry the posting once. Do not retry repeatedly, as this can create duplicate documents.

Escalation: Escalate to ERP Finance Support with the message number if the posting still fails, or immediately if month-end closing is affected.
