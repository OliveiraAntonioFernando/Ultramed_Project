"""Testes de segurança complementares."""

from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from core_gestao.models import Exame, Fatura, Paciente, Plano
from core_gestao.plano_utils import (
    gerar_checkout_token,
    validar_checkout_token,
)


class CheckoutTokenHardeningTests(TestCase):
    def setUp(self):
        self.plano = Plano.objects.create(nome="MASTER", descricao="", valor_anual=59.90)
        self.paciente = Paciente.objects.create(
            nome_completo="Token Test",
            cpf="11122233344",
            telefone="94000000000",
            data_nascimento=date(1990, 1, 1),
            sexo="M",
            is_titular=True,
            plano=self.plano,
        )
        self.outro = Paciente.objects.create(
            nome_completo="Outro",
            cpf="99988877766",
            telefone="94000000001",
            data_nascimento=date(1991, 1, 1),
            sexo="F",
            is_titular=True,
            plano=self.plano,
        )
        self.fatura = Fatura.objects.create(
            paciente=self.paciente,
            plano=self.plano,
            valor=718.80,
            data_vencimento=date(2026, 6, 14),
            status="PENDENTE",
            metodo_pagamento="PIX",
        )

    def test_token_rejeita_paciente_diferente(self):
        token = gerar_checkout_token(self.fatura.id, self.outro.id, self.plano.id)
        self.assertFalse(
            validar_checkout_token(
                token, self.fatura.id, self.paciente.id, self.plano.id
            )
        )

    def test_token_valido_com_fatura(self):
        token = gerar_checkout_token(
            self.fatura.id, self.paciente.id, self.plano.id
        )
        self.assertTrue(
            validar_checkout_token(
                token, self.fatura.id, self.paciente.id, self.plano.id
            )
        )


class MediaProtegidaTests(TestCase):
    def setUp(self):
        self.plano = Plano.objects.create(nome="ESSENCIAL", descricao="", valor_anual=44.90)
        self.paciente = Paciente.objects.create(
            nome_completo="Media Test",
            cpf="55566677788",
            telefone="94000000002",
            data_nascimento=date(1988, 2, 2),
            sexo="M",
            is_titular=True,
            plano=self.plano,
        )
        User.objects.create_user(username="55566677788", password="55566677788")
        self.exame = Exame.objects.create(
            paciente=self.paciente,
            nome_exame="USG Teste",
        )

    def test_anonimo_nao_baixa_exame(self):
        url = reverse("sistema_interno:download_exame_arquivo", args=[self.exame.id])
        r = Client(HTTP_HOST="ultramedsaudexingu.com.br").get(url)
        self.assertEqual(r.status_code, 302)

    def test_paciente_baixa_proprio_exame_sem_arquivo_404(self):
        c = Client(HTTP_HOST="ultramedsaudexingu.com.br")
        c.login(username="55566677788", password="55566677788")
        url = reverse("sistema_interno:download_exame_arquivo", args=[self.exame.id])
        r = c.get(url)
        self.assertEqual(r.status_code, 404)


class CadastroDuplicadoTests(TestCase):
    def setUp(self):
        Plano.objects.create(nome="ESSENCIAL", descricao="", valor_anual=44.90)
        Paciente.objects.create(
            nome_completo="Existente",
            cpf="12312312300",
            telefone="94000000003",
            data_nascimento=date(1985, 5, 5),
            sexo="M",
            is_titular=True,
        )

    def test_rejeita_cpf_duplicado(self):
        url = reverse("sistema_interno:cadastro_plano", kwargs={"plano_nome": "Essencial"})
        r = Client(HTTP_HOST="ultramedsaudexingu.com.br").post(
            url,
            {
                "titular_nome": "Duplicado",
                "titular_cpf": "12312312300",
                "titular_nascimento": "1990-01-01",
                "titular_sexo": "M",
                "titular_telefone": "94000000004",
                "titular_email": "dup@test.com",
                "plano_tipo": "Essencial",
            },
        )
        self.assertEqual(r.status_code, 400)
