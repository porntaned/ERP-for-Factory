from config.readonly_admin import register_read_only

from .models import LotDispositionEvent

register_read_only(LotDispositionEvent)
