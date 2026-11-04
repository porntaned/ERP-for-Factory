from django import template

from demo.quantities import format_quantity

register = template.Library()
register.filter("quantity", format_quantity)
