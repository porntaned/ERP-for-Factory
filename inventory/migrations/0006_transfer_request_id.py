from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("inventory", "0005_stock_transfer")]
    operations = [
        migrations.AddField(
            model_name="stocktransfer",
            name="request_id",
            field=models.UUIDField(null=True, unique=True),
        ),
    ]
