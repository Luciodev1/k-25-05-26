from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('outflows', '0002_outflow_customer_outflow_quantity_delivered_delivery'),
    ]

    operations = [
        migrations.AlterField(
            model_name='outflow',
            name='customer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='outflows', to='customers.customer'),
        ),
    ]
