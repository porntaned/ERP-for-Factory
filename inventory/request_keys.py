"""Cross-command request-key checks shared by receipt, transfer and Quality (M4.4.1)."""

from .models import RequestKey


def owned_by_other_command(request_id, command: str) -> bool:
    return RequestKey.objects.filter(request_id=request_id).exclude(command=command).exists()
