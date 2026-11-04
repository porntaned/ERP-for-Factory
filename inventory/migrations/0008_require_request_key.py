from django.db import migrations

# New StockTransfer rows must carry request_id; otherwise they would bypass the shared
# request-key registry. NOT VALID enforces this for new and updated rows only, so legacy
# NULL rows from before 0006 remain as unadopted history. The Django field stays
# null=True for those legacy rows; the database rule is the authority for new writes.


class Migration(migrations.Migration):
    dependencies = [("inventory", "0007_request_key_registry")]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Flush deferred FK checks so ALTER TABLE works even when this migration
                -- runs inside a transaction that already wrote transfer rows.
                SET CONSTRAINTS ALL IMMEDIATE;
                ALTER TABLE inventory_stocktransfer
                    ADD CONSTRAINT transfer_request_id_required
                    CHECK (request_id IS NOT NULL) NOT VALID;
            """,
            reverse_sql="""
                SET CONSTRAINTS ALL IMMEDIATE;
                ALTER TABLE inventory_stocktransfer
                    DROP CONSTRAINT transfer_request_id_required;
            """,
        ),
    ]
