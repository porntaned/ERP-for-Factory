"""Read-only admin: inspect synthetic data without bypassing Inventory/Quality commands.

Posted movements and Quality history are immutable and may only be written by the
authorized commands, so the admin never offers add, change or delete.
"""

from django.contrib import admin


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


def register_read_only(*models):
    for model in models:
        admin.site.register(model, ReadOnlyAdmin)
