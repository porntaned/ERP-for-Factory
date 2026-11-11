from config.readonly_admin import register_read_only

from .models import LotDispositionEvent, LotInspection

# M6.4 (Issue #113): LotInspection joins the read-only admin (M6.1 finding 2).
register_read_only(LotDispositionEvent, LotInspection)
