"""Testes de plano, checkout, descontos e confirmação de fatura."""

from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core_gestao.models import Fatura, Paciente, Plano, Prontuario
from core_gestao.plano_utils import (
    avaliar_desconto_procedimento,
    calcular_valor_com_desconto,
    gerar_acesso_checkout,
    gerar_checkout_token,
    max_dependentes_plano,
    percentual_desconto,
    resolver_plano,
    validar_acesso_checkout,
    validar_checkout_token,
    valor_checkout_plano,
    valores_mp_coincidem,
)
from core_gestao.procedimentos_catalogo import procedimento_por_id
from core_gestao.views import _confirmar_fatura_paga


class PlanoUtilsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.essencial = Plano.objects.create(
            nome="ESSENCIAL", descricao="Teste", valor_anual=44.90
        )
        cls.master = Plano.objects.create(
            nome="MASTER", descricao="Teste", valor_anual=59.90
        )
        cls.empresarial = Plano.objects.create(
            nome="EMPRESARIAL", descricao="Teste", valor_anual=99.90
        )

    def test_resolver_plano_pelo_formulario(self):
        plano = resolver_plano(tipo="Master")
        self.assertEqual(plano.nome, "MASTER")

    def test_valor_checkout_anualiza_mensal(self):
        self.assertEqual(valor_checkout_plano(self.essencial), round(44.90 * 12, 2))

    def test_tokens_checkout(self):
        token = gerar_acesso_checkout(1, 2)
        self.assertTrue(validar_acesso_checkout(token, 1, 2))
        self.assertFalse(validar_acesso_checkout(token, 9, 2))

        pay_token = gerar_checkout_token(10, 1, 2)
        self.assertTrue(validar_checkout_token(pay_token, 10))
        self.assertFalse(validar_checkout_token(pay_token, 11))

    def test_max_dependentes(self):
        self.assertEqual(max_dependentes_plano(self.essencial), 2)
        self.assertEqual(max_dependentes_plano(self.master), 5)

    def test_valores_mp_coincidem(self):
        self.assertTrue(valores_mp_coincidem("538.80", 538.799))
        self.assertFalse(valores_mp_coincidem("100.00", 50.00))


class DescontoPlanoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.plano = Plano.objects.create(
            nome="ESSENCIAL", descricao="Teste", valor_anual=44.90
        )
        cls.paciente = Paciente.objects.create(
            nome_completo="Titular Desconto",
            cpf="12345678901",
            telefone="94000000099",
            data_nascimento=date(1990, 1, 1),
            sexo="M",
            is_titular=True,
            plano=cls.plano,
            vencimento_plano=date(2030, 1, 1),
        )

    def test_essencial_primeiro_atendimento_30(self):
        self.assertEqual(
            percentual_desconto(self.paciente, procedimento_id="usg_abdomen"), 0.30
        )
        self.assertEqual(
            calcular_valor_com_desconto(
                self.paciente, 100, procedimento_id="usg_abdomen"
            ),
            70.0,
        )

    def test_essencial_segundo_atendimento_mes_20(self):
        Prontuario.objects.create(
            paciente=self.paciente,
            medico=User.objects.create_user(username="medtest", password="x"),
            evolucao="ok",
        )
        self.assertEqual(
            percentual_desconto(self.paciente, procedimento_id="holter_24h"), 0.20
        )

    def test_empresarial_lab_vs_consulta(self):
        emp = Plano.objects.create(nome="EMPRESARIAL", descricao="", valor_anual=99)
        self.paciente.plano = emp
        self.paciente.save()
        self.assertEqual(
            percentual_desconto(self.paciente, procedimento_id="lab_hemograma"), 0.40
        )
        self.assertEqual(
            percentual_desconto(self.paciente, procedimento_id="consulta_clinica"), 0.30
        )


class CoberturaProcedimentoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.essencial = Plano.objects.create(
            nome="ESSENCIAL", descricao="", valor_anual=44.90
        )
        cls.master = Plano.objects.create(
            nome="MASTER", descricao="", valor_anual=59.90
        )
        cls.empresarial = Plano.objects.create(
            nome="EMPRESARIAL", descricao="", valor_anual=69.90
        )
        cls.venc = date(2030, 1, 1)

    def _paciente(self, plano):
        return Paciente.objects.create(
            nome_completo=f"Pac {plano.nome}",
            cpf=f"100000000{plano.id}",
            telefone="94000000001",
            data_nascimento=date(1990, 1, 1),
            sexo="M",
            is_titular=True,
            plano=plano,
            vencimento_plano=self.venc,
        )

    def test_essencial_cobre_usg_nao_endoscopia(self):
        p = self._paciente(self.essencial)
        self.assertEqual(percentual_desconto(p, procedimento_id="usg_abdomen"), 0.30)
        self.assertEqual(percentual_desconto(p, procedimento_id="endoscopia_digestiva"), 0.0)

    def test_master_cobre_consulta_e_endoscopia(self):
        p = self._paciente(self.master)
        self.assertEqual(percentual_desconto(p, procedimento_id="consulta_clinica"), 0.30)
        self.assertEqual(percentual_desconto(p, procedimento_id="endoscopia_digestiva"), 0.30)

    def test_essencial_nao_cobre_consulta(self):
        p = self._paciente(self.essencial)
        info = avaliar_desconto_procedimento(p, procedimento_id="consulta_clinica")
        self.assertFalse(info["coberto"])

    def test_empresarial_nao_cobre_procedimento_fora_lista(self):
        p = self._paciente(self.empresarial)
        self.assertEqual(percentual_desconto(p, procedimento_id="id_invalido_xyz"), 0.0)

    def test_calcular_valor_sem_cobertura_mantem_tabela(self):
        p = self._paciente(self.essencial)
        self.assertEqual(
            calcular_valor_com_desconto(p, 200, procedimento_id="endoscopia_digestiva"),
            200.0,
        )


class CatalogoProcedimentosTests(TestCase):
    def test_todos_ids_unicos(self):
        from core_gestao.procedimentos_catalogo import CATALOGO_PROCEDIMENTOS

        ids = [p["id"] for p in CATALOGO_PROCEDIMENTOS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_lookup_catalogo(self):
        proc = procedimento_por_id("usg_abdomen")
        self.assertIsNotNone(proc)
        self.assertEqual(proc["nome"], "USG Abdômen")
        self.assertIn("ESSENCIAL", proc["planos"])


class ConfirmarFaturaTests(TestCase):
    def test_confirmar_ativa_plano_e_vencimento(self):
        plano = Plano.objects.create(nome="MASTER", descricao="", valor_anual=59.90)
        paciente = Paciente.objects.create(
            nome_completo="Pac Fatura",
            cpf="55544433322",
            telefone="94000000088",
            data_nascimento=date(1988, 8, 8),
            sexo="F",
            is_titular=True,
        )
        fatura = Fatura.objects.create(
            paciente=paciente,
            plano=plano,
            valor=718.80,
            data_vencimento=timezone.now().date(),
            status="PENDENTE",
            metodo_pagamento="PIX",
        )
        ok = _confirmar_fatura_paga(fatura, "mp-123", 718.80)
        self.assertTrue(ok)
        paciente.refresh_from_db()
        fatura.refresh_from_db()
        self.assertEqual(fatura.status, "PAGO")
        self.assertEqual(paciente.plano_id, plano.id)
        self.assertIsNotNone(paciente.vencimento_plano)

    def test_rejeita_valor_divergente(self):
        plano = Plano.objects.create(nome="ESSENCIAL", descricao="", valor_anual=44.90)
        paciente = Paciente.objects.create(
            nome_completo="Pac Divergente",
            cpf="44433322211",
            telefone="94000000077",
            data_nascimento=date(1987, 7, 7),
            sexo="M",
            is_titular=True,
        )
        fatura = Fatura.objects.create(
            paciente=paciente,
            plano=plano,
            valor=538.80,
            data_vencimento=timezone.now().date(),
            status="PENDENTE",
            metodo_pagamento="PIX",
        )
        ok = _confirmar_fatura_paga(fatura, "mp-999", 1.00)
        self.assertFalse(ok)
        fatura.refresh_from_db()
        self.assertEqual(fatura.status, "PENDENTE")


class CadastroCheckoutFlowTests(TestCase):
    def test_cadastro_redireciona_com_token(self):
        Plano.objects.create(nome="ESSENCIAL", descricao="", valor_anual=44.90)
        url = reverse("sistema_interno:cadastro_plano", kwargs={"plano_nome": "Essencial"})
        r = self.client.post(
            url,
            {
                "titular_nome": "Novo Titular",
                "titular_cpf": "33322211100",
                "titular_nascimento": "1995-05-05",
                "titular_sexo": "M",
                "titular_telefone": "94000000066",
                "titular_email": "novo@teste.com",
                "plano_tipo": "Essencial",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn("t=", r.url)
        self.assertIn("/checkout/pagamento/", r.url)

        user = User.objects.get(username="33322211100")
        self.assertTrue(user.check_password("33322211100"))
