"""M5.2c (Issue #81): a shortfall reason is stored when, and only when, an order closes short.

Net output (OUTPUT - reversed OUTPUT) below the order quantity at OPEN -> CLOSED requires a
nonblank reason; complete output refuses one. Orders closed before this migration are left as
they are: the rule checks the transition, not existing rows.
"""

from django.conf import settings
from django.db import migrations, models

FORWARD = r"""
CREATE FUNCTION manufacturing_guard_order_shortfall()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'OPEN' AND NEW.status = 'CLOSED'
       AND (manufacturing_order_net_output(NEW.id) < NEW.quantity)
           IS DISTINCT FROM (NEW.shortfall_reason IS NOT NULL) THEN
        RAISE EXCEPTION 'a shortfall reason is given exactly when net output is short'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER manufacturing_order_shortfall
BEFORE UPDATE ON manufacturing_productionorder FOR EACH ROW
EXECUTE FUNCTION manufacturing_guard_order_shortfall();
"""

REVERSE = r"""
DROP TRIGGER manufacturing_order_shortfall ON manufacturing_productionorder;
DROP FUNCTION manufacturing_guard_order_shortfall();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("facilities", "0001_initial"),
        ("manufacturing", "0007_posting_reversal_rules"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="productionorder",
            name="shortfall_reason",
            field=models.TextField(null=True),
        ),
        migrations.AddConstraint(
            model_name="productionorder",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("shortfall_reason__isnull", True),
                    models.Q(
                        ("status", "CLOSED"),
                        models.Q(("shortfall_reason__regex", "^\\s*$"), _negated=True),
                    ),
                    _connector="OR",
                ),
                name="order_shortfall_reason_closed_nonblank",
            ),
        ),
        migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE),
    ]
