"""
Testes de URLs, redirecionamentos e perfis (master, recepção, médico, paciente).
Execute: python manage.py test core_gestao.tests
"""

from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core_gestao.models import Agenda, ChamadaPainel, Paciente, Plano


class StaffUserMixin:
    """Cria usuários padrão do sistema interno."""

    @classmethod
    def setUpTestData(cls):
        cls.password = "senha-teste-123"
        User.objects.create_user(username="recepcao", password=cls.password)
        User.objects.create_user(username="medico", password=cls.password)
        User.objects.create_user(username="master", password=cls.password)
        User.objects.create_user(username="11122233344", password=cls.password)


class AnonymousAccessTests(TestCase):
    def test_master_dashboard_redirects_login(self):
        r = self.client.get(reverse("sistema_interno:master_dashboard"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("sistema_interno:login"), r.url)

    def test_agenda_redirects_login(self):
        r = self.client.get(reverse("sistema_interno:agenda_view"))
        self.assertEqual(r.status_code, 302)


class ReceptionAccessTests(StaffUserMixin, TestCase):
    def setUp(self):
        self.client.login(username="recepcao", password=self.password)

    def test_agenda_ok(self):
        r = self.client.get(reverse("sistema_interno:agenda_view"))
        self.assertEqual(r.status_code, 200)

    def test_agenda_with_data_param(self):
        r = self.client.get(
            reverse("sistema_interno:agenda_view"),
            {"data": "2026-04-15"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "2026-04-15")

    def test_painel_colaborador_ok(self):
        r = self.client.get(reverse("sistema_interno:painel_colaborador"))
        self.assertEqual(r.status_code, 200)

    def test_fatura_create_ok(self):
        r = self.client.get(reverse("sistema_interno:fatura_create"))
        self.assertEqual(r.status_code, 200)

    def test_master_dashboard_forbidden(self):
        r = self.client.get(reverse("sistema_interno:master_dashboard"))
        self.assertEqual(r.status_code, 302)

    def test_fatura_store_post_redirects_to_colaborador(self):
        p = Paciente.objects.create(
            nome_completo="Paciente Fatura",
            cpf="77766655544",
            telefone="94000000003",
            data_nascimento=date(1991, 3, 3),
            sexo="M",
            is_titular=True,
        )
        r = self.client.post(
            reverse("sistema_interno:fatura_store"),
            {
                "paciente": str(p.id),
                "metodo_pagamento": "PIX",
                "valor": "50.00",
                "data_pagamento": "2026-01-15",
                "status": "PENDENTE",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("sistema_interno:painel_colaborador"))


class MasterAccessTests(StaffUserMixin, TestCase):
    def setUp(self):
        self.client.login(username="master", password=self.password)

    def test_master_dashboard_ok(self):
        r = self.client.get(reverse("sistema_interno:master_dashboard"))
        self.assertEqual(r.status_code, 200)

    def test_fatura_create_ok(self):
        r = self.client.get(reverse("sistema_interno:fatura_create"))
        self.assertEqual(r.status_code, 200)

    def test_agenda_ok(self):
        r = self.client.get(reverse("sistema_interno:agenda_view"))
        self.assertEqual(r.status_code, 200)

    def test_fatura_store_post_redirects_to_master_dashboard(self):
        p = Paciente.objects.create(
            nome_completo="Paciente Fatura Master",
            cpf="66655544433",
            telefone="94000000004",
            data_nascimento=date(1993, 4, 4),
            sexo="F",
            is_titular=True,
        )
        r = self.client.post(
            reverse("sistema_interno:fatura_store"),
            {
                "paciente": str(p.id),
                "metodo_pagamento": "PIX",
                "valor": "80.00",
                "data_pagamento": "2026-02-01",
                "status": "PENDENTE",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("sistema_interno:master_dashboard"))


class MedicoAccessTests(StaffUserMixin, TestCase):
    def setUp(self):
        self.client.login(username="medico", password=self.password)

    def test_painel_medico_ok(self):
        r = self.client.get(reverse("sistema_interno:painel_medico"))
        self.assertEqual(r.status_code, 200)

    def test_agenda_forbidden(self):
        r = self.client.get(reverse("sistema_interno:agenda_view"))
        self.assertEqual(r.status_code, 302)

    def test_fatura_create_forbidden(self):
        r = self.client.get(reverse("sistema_interno:fatura_create"))
        self.assertEqual(r.status_code, 302)

    def test_master_dashboard_forbidden(self):
        r = self.client.get(reverse("sistema_interno:master_dashboard"))
        self.assertEqual(r.status_code, 302)


class ReceptionClinicalLockTests(StaffUserMixin, TestCase):
    """Recepção não deve acessar dados clínicos sensíveis via API."""

    def setUp(self):
        self.client.login(username="recepcao", password=self.password)
        self.paciente = Paciente.objects.create(
            nome_completo="Paciente Clinico",
            cpf="55544433322",
            telefone="94000000009",
            data_nascimento=date(1990, 1, 1),
            sexo="M",
            is_titular=True,
        )

    def test_recepcao_nao_le_ultima_receita(self):
        r = self.client.get(
            reverse("sistema_interno:api_ultima_receita", args=[self.paciente.id])
        )
        self.assertEqual(r.status_code, 403)

    def test_recepcao_nao_classifica_cronico(self):
        r = self.client.post(
            reverse("sistema_interno:salvar_doencas", args=[self.paciente.id]),
            {"doencas[]": ["DIABETES"]},
        )
        self.assertEqual(r.status_code, 403)

    def test_recepcao_nao_abre_prontuario(self):
        r = self.client.get(
            reverse("sistema_interno:prontuario_view", args=[self.paciente.id])
        )
        self.assertEqual(r.status_code, 302)

    def test_recepcao_nao_abre_master(self):
        r = self.client.get(reverse("sistema_interno:master_dashboard"))
        self.assertEqual(r.status_code, 302)


class PacienteAccessTests(StaffUserMixin, TestCase):
    def setUp(self):
        self.client.login(username="11122233344", password=self.password)

    def test_cliente_list_forbidden(self):
        r = self.client.get(reverse("sistema_interno:cliente_list"))
        self.assertEqual(r.status_code, 302)

    def test_painel_paciente_ok(self):
        Paciente.objects.create(
            nome_completo="Titular Teste",
            cpf="11122233344",
            telefone="94000000000",
            data_nascimento=date(1990, 1, 1),
            sexo="M",
            is_titular=True,
        )
        r = self.client.get(reverse("sistema_interno:painel_paciente"))
        self.assertEqual(r.status_code, 200)


class ApiBuscarPacienteTests(StaffUserMixin, TestCase):
    def setUp(self):
        self.client.login(username="recepcao", password=self.password)
        Paciente.objects.create(
            nome_completo="Maria Busca Teste",
            cpf="99988877766",
            telefone="94000000001",
            data_nascimento=date(1985, 5, 5),
            sexo="F",
            is_titular=True,
        )

    def test_busca_retorna_json(self):
        url = reverse("sistema_interno:api_buscar_paciente")
        r = self.client.get(url, {"q": "Maria"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("results", data)
        self.assertTrue(len(data["results"]) >= 1)


class AgendaCheckinTests(StaffUserMixin, TestCase):
    def setUp(self):
        self.client.login(username="recepcao", password=self.password)
        self.plano = Plano.objects.create(
            nome="ESSENCIAL",
            descricao="Teste",
            valor_anual=100.00,
        )
        self.paciente = Paciente.objects.create(
            nome_completo="Paciente Agenda",
            cpf="88877766655",
            telefone="94000000002",
            data_nascimento=date(1992, 2, 2),
            sexo="M",
            is_titular=True,
            plano=self.plano,
            vencimento_plano=date(2030, 1, 1),
        )
        self.ag = Agenda.objects.create(
            paciente=self.paciente,
            data=date(2026, 6, 10),
            hora=time(9, 30),
            tipo="CONSULTA",
            status="AGENDADO",
        )

    def test_checkin_atualiza_status_e_redirect(self):
        url = reverse("sistema_interno:agenda_view")
        r = self.client.post(
            f"{url}?data=2026-06-10",
            {
                "agenda_checkin_id": str(self.ag.id),
                "data": "2026-06-10",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.ag.refresh_from_db()
        self.assertEqual(self.ag.status, "CHEGOU")
        # Check-in coloca o paciente na fila do dia corrente
        self.assertEqual(self.ag.data, timezone.now().date())

    def test_checkin_get_atalho_recepcao(self):
        url = reverse("sistema_interno:agenda_view")
        r = self.client.get(url, {"status": "CHEGOU", "id": str(self.ag.id)})
        self.assertEqual(r.status_code, 302)
        self.ag.refresh_from_db()
        self.assertEqual(self.ag.status, "CHEGOU")
        self.assertEqual(self.ag.data, timezone.now().date())

    def test_checkin_no_painel_recepcao(self):
        url = reverse("sistema_interno:painel_colaborador")
        # garante agendamento de hoje
        self.ag.data = timezone.now().date()
        self.ag.status = "AGENDADO"
        self.ag.save()
        r = self.client.post(url, {"agenda_checkin_id": str(self.ag.id)})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, url)
        self.ag.refresh_from_db()
        self.assertEqual(self.ag.status, "CHEGOU")


class TvEsperaTests(StaffUserMixin, TestCase):
    def setUp(self):
        self.plano = Plano.objects.create(
            nome="ESSENCIAL",
            descricao="Teste",
            valor_anual=100.00,
        )
        self.paciente = Paciente.objects.create(
            nome_completo="Paciente TV",
            cpf="77766655544",
            telefone="94000000003",
            data_nascimento=date(1990, 1, 1),
            sexo="F",
            is_titular=True,
            plano=self.plano,
            vencimento_plano=date(2030, 1, 1),
        )

    def test_tv_espera_requer_equipe(self):
        r = self.client.get(reverse("sistema_interno:tv_espera"))
        self.assertEqual(r.status_code, 302)

    def test_tv_espera_ok_recepcao(self):
        self.client.login(username="recepcao", password=self.password)
        r = self.client.get(reverse("sistema_interno:tv_espera"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Sala de espera")

    def test_medico_chama_na_tv(self):
        self.client.login(username="medico", password=self.password)
        url = reverse("sistema_interno:chamar_paciente_tv", args=[self.paciente.id])
        r = self.client.post(url, {"consultorio": "Consultório 1"})
        self.assertEqual(r.status_code, 302)
        self.assertIn(
            reverse("sistema_interno:prontuario_view", args=[self.paciente.id]),
            r.url,
        )
        chamada = ChamadaPainel.objects.get(pk=1)
        self.assertEqual(chamada.paciente_nome, "Paciente TV")
        api = self.client.get(reverse("sistema_interno:api_tv_chamada"))
        self.assertEqual(api.status_code, 200)
        self.assertTrue(api.json()["ativa"])

    def test_medico_chama_tv_fica_na_fila(self):
        self.client.login(username="medico", password=self.password)
        url = reverse("sistema_interno:chamar_paciente_tv", args=[self.paciente.id])
        r = self.client.post(
            url, {"consultorio": "Consultório 1", "destino": "fila"}
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("sistema_interno:painel_medico"))

    def test_medico_repete_chamado_no_prontuario(self):
        self.client.login(username="medico", password=self.password)
        url = reverse("sistema_interno:chamar_paciente_tv", args=[self.paciente.id])
        r = self.client.post(
            url, {"consultorio": "Consultório 1", "destino": "repetir"}
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn(
            reverse("sistema_interno:prontuario_view", args=[self.paciente.id]),
            r.url,
        )
