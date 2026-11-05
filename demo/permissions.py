"""Permission-aware display. Commands still enforce authority; this only decides what to show."""

from access_control.policies import has_warehouse_role, warehouses_for_user


def movable_warehouses(user):
    return warehouses_for_user(user, ["WAREHOUSE"]).select_related("plant").order_by("code")


def can_approve_all(user, warehouses):
    return all(has_warehouse_role(user, warehouse, ["APPROVER"]) for warehouse in warehouses)


def navigation(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {
        "can_move_stock": movable_warehouses(user).exists(),
        "can_reverse": warehouses_for_user(user, ["APPROVER"]).exists(),
    }


def production_warehouses(user):
    return warehouses_for_user(user, ["PRODUCTION"]).select_related("plant").order_by("code")


def order_actions(user, order):
    """Which record buttons to show on an order (M5.5). Nothing once the order is not OPEN."""
    open_ = order.status == "OPEN"
    line, output = order.line_warehouse, order.output_warehouse
    produces = open_ and all(has_warehouse_role(user, w, ["PRODUCTION"]) for w in (line, output))
    return {
        "record": produces,
        "scrap": open_ and has_warehouse_role(user, line, ["APPROVER"]),
        "reverse_line": open_ and has_warehouse_role(user, line, ["APPROVER"]),
        "reverse_output": open_ and has_warehouse_role(user, output, ["APPROVER"]),
    }
