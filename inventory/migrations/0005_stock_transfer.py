import django.db.models.deletion
from django.db import migrations, models
from django.db.models.functions import Now


class Migration(migrations.Migration):
    dependencies = [("inventory", "0004_stock_receipt")]

    operations = [
        migrations.CreateModel(
            name="StockTransfer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(db_default=Now(), editable=False)),
                (
                    "source_entry",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transfer_out",
                        to="inventory.stockledgerentry",
                    ),
                ),
                (
                    "destination_entry",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transfer_in",
                        to="inventory.stockledgerentry",
                    ),
                ),
            ],
        ),
        migrations.RunSQL(
            sql="""
                ALTER TABLE inventory_stocktransfer ALTER COLUMN id SET GENERATED ALWAYS;

                CREATE FUNCTION inventory_validate_transfer_link()
                RETURNS trigger LANGUAGE plpgsql VOLATILE AS $$
                DECLARE
                    source_row inventory_stockledgerentry%ROWTYPE;
                    destination_row inventory_stockledgerentry%ROWTYPE;
                    source_plant bigint;
                    destination_plant bigint;
                BEGIN
                    IF current_setting('transaction_isolation') <> 'read committed' THEN
                        RAISE EXCEPTION 'transfer links require READ COMMITTED'
                            USING ERRCODE = '23514';
                    END IF;
                    -- Serialize ownership with receipt links and other transfer links.
                    PERFORM id FROM inventory_stockledgerentry
                    WHERE id IN (NEW.source_entry_id, NEW.destination_entry_id)
                    ORDER BY id FOR UPDATE;
                    SELECT * INTO source_row FROM inventory_stockledgerentry
                    WHERE id = NEW.source_entry_id;
                    SELECT * INTO destination_row FROM inventory_stockledgerentry
                    WHERE id = NEW.destination_entry_id;
                    IF source_row.id IS NULL OR destination_row.id IS NULL
                        OR source_row.id = destination_row.id
                        OR NOT (source_row.quantity_delta < 0)
                        OR NOT (destination_row.quantity_delta > 0)
                        OR source_row.quantity_delta + destination_row.quantity_delta <> 0
                        OR source_row.lot_id <> destination_row.lot_id
                        OR source_row.actor_id <> destination_row.actor_id
                        OR source_row.reason <> destination_row.reason
                        OR source_row.warehouse_id = destination_row.warehouse_id THEN
                        RAISE EXCEPTION 'transfer requires matching debit and credit entries'
                            USING ERRCODE = '23514';
                    END IF;
                    SELECT plant_id INTO source_plant FROM facilities_warehouse
                    WHERE id = source_row.warehouse_id;
                    SELECT plant_id INTO destination_plant FROM facilities_warehouse
                    WHERE id = destination_row.warehouse_id;
                    IF source_plant IS DISTINCT FROM destination_plant THEN
                        RAISE EXCEPTION 'transfer warehouses must share one Plant'
                            USING ERRCODE = '23514';
                    END IF;
                    IF EXISTS (SELECT 1 FROM inventory_stockreceipt
                               WHERE ledger_entry_id = NEW.destination_entry_id) THEN
                        RAISE EXCEPTION 'receipt entry cannot belong to transfer'
                            USING ERRCODE = '23514';
                    END IF;
                    NEW.created_at := statement_timestamp();
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER inventory_transfer_link
                BEFORE INSERT ON inventory_stocktransfer FOR EACH ROW
                EXECUTE FUNCTION inventory_validate_transfer_link();
                CREATE TRIGGER inventory_transfer_immutable
                BEFORE UPDATE OR DELETE ON inventory_stocktransfer FOR EACH ROW
                EXECUTE FUNCTION inventory_reject_stock_rewrite();

                CREATE FUNCTION inventory_receipt_exclude_transfer()
                RETURNS trigger LANGUAGE plpgsql VOLATILE AS $$
                BEGIN
                    IF current_setting('transaction_isolation') <> 'read committed' THEN
                        RAISE EXCEPTION 'receipt links require READ COMMITTED'
                            USING ERRCODE = '23514';
                    END IF;
                    PERFORM id FROM inventory_stockledgerentry
                    WHERE id = NEW.ledger_entry_id FOR UPDATE;
                    IF EXISTS (SELECT 1 FROM inventory_stocktransfer
                               WHERE destination_entry_id = NEW.ledger_entry_id) THEN
                        RAISE EXCEPTION 'transfer entry cannot belong to receipt'
                            USING ERRCODE = '23514';
                    END IF;
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER inventory_receipt_transfer_exclusion
                BEFORE INSERT ON inventory_stockreceipt FOR EACH ROW
                EXECUTE FUNCTION inventory_receipt_exclude_transfer();
            """,
            reverse_sql="""
                DROP TRIGGER inventory_receipt_transfer_exclusion ON inventory_stockreceipt;
                DROP FUNCTION inventory_receipt_exclude_transfer();
                DROP TRIGGER inventory_transfer_immutable ON inventory_stocktransfer;
                DROP TRIGGER inventory_transfer_link ON inventory_stocktransfer;
                DROP FUNCTION inventory_validate_transfer_link();
                ALTER TABLE inventory_stocktransfer ALTER COLUMN id SET GENERATED BY DEFAULT;
            """,
        ),
    ]
