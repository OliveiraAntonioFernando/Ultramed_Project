# Generated manually — vínculo plano na fatura (checkout MP)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core_gestao", "0013_alter_fatura_mercadopago_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="fatura",
            name="plano",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="faturas",
                to="core_gestao.plano",
            ),
        ),
    ]
