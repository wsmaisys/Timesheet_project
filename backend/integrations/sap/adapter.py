"""SAP integration adapter boundary (SRS §16 & §19).

No automatic posting to SAP CATS, S/4HANA WBS, or payroll occurs in MVP.
This module defines the staging contract and pure mapper for Phase 5.
"""

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class SAPCATSRecord:
    employee_code: str
    work_date: date
    project_code: str
    task_code: str
    sap_module: str | None
    sap_workstream: str | None
    hours_decimal: float
    billable: bool
    timesheet_id: str
    entry_id: str


class SAPTimeAdapter(Protocol):
    def stage_approved_entries(self, records: list[SAPCATSRecord], idempotency_key: str) -> dict:
        ...


class NullSAPAdapter:
    """No-op default adapter for MVP deployments without live SAP integration."""

    def stage_approved_entries(self, records: list[SAPCATSRecord], idempotency_key: str) -> dict:
        return {
            "status": "STAGED_NOOP",
            "record_count": len(records),
            "idempotency_key": idempotency_key,
        }


def build_cats_staging_payload(timesheet) -> list[SAPCATSRecord]:
    if timesheet.status != "APPROVED":
        raise ValueError("Only APPROVED timesheets may be staged for SAP export.")

    records: list[SAPCATSRecord] = []
    for entry in timesheet.entries.select_related("project", "task").all():
        records.append(
            SAPCATSRecord(
                employee_code=timesheet.user.employee_code,
                work_date=entry.work_date,
                project_code=entry.project.code,
                task_code=entry.task.code,
                sap_module=entry.task.sap_module,
                sap_workstream=entry.task.sap_workstream,
                hours_decimal=round(entry.duration_minutes / 60.0, 2),
                billable=entry.billable,
                timesheet_id=str(timesheet.id),
                entry_id=str(entry.id),
            )
        )
    return records
