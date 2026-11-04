from config.readonly_admin import register_read_only

from .models import Organization, Plant, Warehouse

register_read_only(Organization, Plant, Warehouse)
