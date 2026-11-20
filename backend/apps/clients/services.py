from django.db import IntegrityError, transaction

from apps.audit.services import record_audit_event
from common.exceptions import DomainError

from .models import Client


def create_client(*, actor, code: str, name: str) -> Client:
    cleaned_code = code.strip().upper()
    cleaned_name = name.strip()
    if not cleaned_code or not cleaned_name:
        raise DomainError("VALIDATION_ERROR", "Client code and name are required.")

    if Client.objects.filter(code__iexact=cleaned_code).exists():
        raise DomainError(
            code="CLIENT_CODE_EXISTS",
            message=f"Client with code '{cleaned_code}' already exists.",
            status_code=409,
        )

    with transaction.atomic():
        try:
            client = Client.objects.create(code=cleaned_code, name=cleaned_name, status=Client.Status.ACTIVE)
        except IntegrityError:
            raise DomainError(
                code="CLIENT_CODE_EXISTS",
                message=f"Client with code '{cleaned_code}' already exists.",
                status_code=409,
            )
        record_audit_event(
            actor=actor,
            action="CLIENT_CREATED",
            entity_type="Client",
            entity_id=client.id,
            after_json={"code": client.code, "name": client.name, "status": client.status},
        )
        return client


def update_client(*, actor, client: Client, updates: dict) -> Client:
    before = {"code": client.code, "name": client.name, "status": client.status}
    with transaction.atomic():
        if "name" in updates:
            cleaned_name = updates["name"].strip()
            if not cleaned_name:
                raise DomainError("VALIDATION_ERROR", "Client name cannot be empty.")
            client.name = cleaned_name
        if "status" in updates:
            client.status = updates["status"]
        client.save()
        record_audit_event(
            actor=actor,
            action="CLIENT_UPDATED",
            entity_type="Client",
            entity_id=client.id,
            before_json=before,
            after_json={"code": client.code, "name": client.name, "status": client.status},
        )
    return client
