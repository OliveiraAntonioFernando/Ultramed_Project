# Generated manually for FaturaLicencaSistema

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core_gestao", "0015_chamada_painel"),
    ]

    operations = [
        migrations.CreateModel(
            name="FaturaLicencaSistema",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "referencia",
                    models.CharField(
                        help_text="Competência AAAA-MM (ex.: 2026-08)",
                        max_length=7,
                        unique=True,
                    ),
                ),
                (
                    "valor",
                    models.DecimalField(
                        decimal_places=2, default=Decimal("399.00"), max_digits=10
                    ),
                ),
                ("data_vencimento", models.DateField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDENTE", "Pendente"),
                            ("PAGO", "Pago"),
                            ("ATRASADO", "Atrasado"),
                        ],
                        default="PENDENTE",
                        max_length=10,
                    ),
                ),
                ("data_pagamento", models.DateField(blank=True, null=True)),
                (
                    "mercadopago_id",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                (
                    "preferencia_id",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                (
                    "checkout_url",
                    models.URLField(blank=True, max_length=500, null=True),
                ),
                (
                    "observacao",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Fatura licença sistema",
                "verbose_name_plural": "Faturas licença sistema",
                "ordering": ["-data_vencimento", "-id"],
            },
        ),
    ]
