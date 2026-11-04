from config.readonly_admin import register_read_only

from .models import (
    Lot,
    RequestKey,
    StockLedgerEntry,
    StockReceipt,
    StockReversal,
    StockTransfer,
)

register_read_only(Lot, StockLedgerEntry, StockReceipt, StockTransfer, StockReversal, RequestKey)
