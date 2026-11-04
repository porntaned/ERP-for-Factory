from django.db import migrations

# Same-timing triggers fire in name order. Rename the registry trigger so it fires AFTER
# quality_lot_disposition_validate_insert, which takes the Lot lock: the shared key is
# then taken last, consistent with Lot -> Item -> Warehouses -> Plant -> request key.


class Migration(migrations.Migration):
    dependencies = [("quality", "0004_request_key_registration")]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TRIGGER quality_disposition_request_key ON quality_lotdispositionevent
                    RENAME TO quality_lot_disposition_zz_request_key;
            """,
            reverse_sql="""
                ALTER TRIGGER quality_lot_disposition_zz_request_key ON quality_lotdispositionevent
                    RENAME TO quality_disposition_request_key;
            """,
        ),
    ]
