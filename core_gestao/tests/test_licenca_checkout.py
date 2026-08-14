from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse

from core_gestao.models import FaturaLicencaSistema
from core_gestao.tests.test_access import StaffUserMixin


@override_settings(
    MERCADO_PAGO_RINAN_ACCESS_TOKEN="TEST-rinan-token",
    MERCADO_PAGO_RINAN_PUBLIC_KEY="TEST-rinan-public",
)
class LicencaCheckoutTests(StaffUserMixin, TestCase):
    def setUp(self):
        self.client.login(username="master", password=self.password)
        self.fatura = FaturaLicencaSistema.objects.create(
            referencia="2026-08",
            valor="399.00",
            data_vencimento=date(2026, 8, 10),
            status="PENDENTE",
        )

    def test_pagar_abre_tela_rinan_nao_redireciona_mp(self):
        r = self.client.get(reverse("sistema_interno:licenca_pagar", args=[self.fatura.id]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "RINAN")
        self.assertContains(r, "Licença Ultramed")
        self.assertNotContains(r, "mercadopago.com/checkout")
        self.assertIsNone(r.get("Location"))

    def test_recepcao_nao_acessa_checkout_licenca(self):
        self.client.logout()
        self.client.login(username="recepcao", password=self.password)
        r = self.client.get(reverse("sistema_interno:licenca_pagar", args=[self.fatura.id]))
        self.assertEqual(r.status_code, 302)
        self.assertNotIn("licenca/pagar", r.url)
