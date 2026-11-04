from config.readonly_admin import register_read_only

from .models import Lot, RequestKey, StockLedgerEntry, StockReceipt, StockTransfer

register_read_only(Lot, StockLedgerEntry, StockReceipt, StockTransfer, RequestKey)
