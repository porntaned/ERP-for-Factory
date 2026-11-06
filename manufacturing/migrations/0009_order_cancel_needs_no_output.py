"""Issue #86: an order with net output cannot be cancelled.

Owner ruling (2026-11-05, option A): OPEN -> CANCELLED is refused while net output
(OUTPUT - reversed OUTPUT) is above zero. Reverse the output first, or close the order (which
needs a shortfall reason when short). The rule checks the transition, so orders cancelled before
this migration are left as they are.
"""

from django.db import migrations

FORWARD = r"""
CREATE FUNCTION manufacturing_guard_order_cancel_output()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'OPEN' AND NEW.status = 'CANCELLED'
       AND manufacturing_order_net_output(NEW.id) > 0 THEN
        RAISE EXCEPTION 'an order with net output cannot be cancelled'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER manufacturing_order_cancel_output
BEFORE UPDATE ON manufacturing_productionorder FOR EACH ROW
EXECUTE FUNCTION manufacturing_guard_order_cancel_output();
"""

REVERSE = r"""
DROP TRIGGER manufacturing_order_cancel_output ON manufacturing_productionorder;
DROP FUNCTION manufacturing_guard_order_cancel_output();
"""


class Migration(migrations.Migration):
    dependencies = [("manufacturing", "0008_order_shortfall_reason")]

    operations = [migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE)]
