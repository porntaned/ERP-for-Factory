from config.readonly_admin import register_read_only

from .models import WarehouseRoleAssignment

register_read_only(WarehouseRoleAssignment)
