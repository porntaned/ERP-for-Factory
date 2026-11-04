from config.readonly_admin import register_read_only

from .models import Item, UnitOfMeasure

register_read_only(UnitOfMeasure, Item)
