from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from operacion.files import validate_soporte

from operacion.models import (
    Actividad,
    EstadoRecaudo,
    Familia,
    Padrino,
    Recaudo,
    ReciboSequence,
)
from operacion.money import money

pytestmark = pytest.mark.django_db


@pytest.fixture
def api(db):
    User = get_user_model()
    user = User.objects.create_user(
        username="admin", password="clave-segura-10", is_staff=True, is_superuser=True
    )
    client = APIClient()
    client.force_login(user)
    client.user = user
    return client


@pytest.fixture
def catalogo(db):
    padrino = Padrino.objects.create(
        nombre_completo="Ana Pérez", telefono="3001234567", correo="ana@example.com"
    )
    familia = Familia.objects.create(
        nombre="Familia Gómez",
        contacto_principal="Luis Gómez",
        telefono="3019876543",
        padrino=padrino,
    )
    actividad = Actividad.objects.create(
        nombre="Entrega de regalos",
        descripcion="Navidad",
        fecha_inicio=date(2026, 11, 1),
        fecha_fin=date(2026, 12, 31),
    )
    ReciboSequence.objects.get_or_create(pk=1, defaults={"ultimo_numero": 0})
    return {"padrino": padrino, "familia": familia, "actividad": actividad}


def test_no_hay_limite_de_padrinos(api):
    for i in range(15):
        response = api.post(
            "/api/padrinos/",
            {
                "nombre_completo": f"Padrino {i}",
                "telefono": f"30000000{i:02d}",
            },
            format="json",
        )
        assert response.status_code == 201, response.content
    assert Padrino.objects.count() == 15


def test_reasignar_familia_conserva_historial(api, catalogo):
    otro = Padrino.objects.create(nombre_completo="Carlos Ruiz", telefono="3021112233")
    familia = catalogo["familia"]
    response = api.post(
        f"/api/familias/{familia.id}/reasignar/",
        {"padrino": str(otro.id), "motivo": "Cambio de zona"},
        format="json",
    )
    assert response.status_code == 200
    familia.refresh_from_db()
    assert familia.padrino_id == otro.id
    historial = api.get(f"/api/familias/{familia.id}/historial/")
    assert historial.status_code == 200
    assert len(historial.json()) == 1
    assert historial.json()[0]["motivo"] == "Cambio de zona"


def test_buscar_familia_por_nombre(api, catalogo):
    response = api.get("/api/familias/buscar/", {"q": "Gómez"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["nombre"] == "Familia Gómez"


def test_confirmar_recaudo_genera_recibo_y_no_mezcla_actividades(api, catalogo):
    otra = Actividad.objects.create(
        nombre="Entrega de uniformes",
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 2, 1),
    )
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    soporte = SimpleUploadedFile("comprobante.png", png, content_type="image/png")
    first = api.post(
        "/api/recaudos/",
        {
            "actividad": str(catalogo["actividad"].id),
            "padrino": str(catalogo["padrino"].id),
            "familia": str(catalogo["familia"].id),
            "valor": "150000.00",
            "medio_pago": "efectivo",
            "concepto": "Aporte regalos",
        },
        format="multipart",
    )
    assert first.status_code == 201, first.content
    data = first.json()
    assert data["numero"] == 1
    assert data["numero_formateado"] == "000001"
    assert data["valor"] == "150000.00"
    assert data["recibo"]
    assert data["soportes"] == []

    second = api.post(
        "/api/recaudos/",
        {
            "actividad": str(otra.id),
            "padrino": str(catalogo["padrino"].id),
            "familia": str(catalogo["familia"].id),
            "valor": "80000.50",
            "medio_pago": "transferencia",
            "referencia_consignacion": "TRX-99",
            "soportes": soporte,
        },
        format="multipart",
    )
    assert second.status_code == 201, second.content
    assert second.json()["numero"] == 2
    assert len(second.json()["soportes"]) == 1

    consultas = api.get("/api/recaudos/", {"actividad": str(catalogo["actividad"].id)})
    payload = consultas.json()
    assert payload["totales"]["total_confirmado"] == "150000.00"
    assert payload["totales"]["cantidad_confirmados"] == 1

    pdf = api.get(f"/api/recaudos/{data['id']}/recibo/")
    assert pdf.status_code == 200
    body = b"".join(pdf.streaming_content)
    assert body.startswith(b"%PDF")


def test_anular_no_reutiliza_numero(api, catalogo):
    r1 = api.post(
        "/api/recaudos/",
        {
            "actividad": str(catalogo["actividad"].id),
            "padrino": str(catalogo["padrino"].id),
            "familia": str(catalogo["familia"].id),
            "valor": "10000",
            "medio_pago": "efectivo",
        },
        format="multipart",
    )
    recaudo_id = r1.json()["id"]
    anula = api.post(
        f"/api/recaudos/{recaudo_id}/anular/",
        {"motivo": "Valor digitado por error"},
        format="json",
    )
    assert anula.status_code == 200
    assert anula.json()["estado"] == EstadoRecaudo.ANULADO
    r2 = api.post(
        "/api/recaudos/",
        {
            "actividad": str(catalogo["actividad"].id),
            "padrino": str(catalogo["padrino"].id),
            "familia": str(catalogo["familia"].id),
            "valor": "20000",
            "medio_pago": "efectivo",
        },
        format="multipart",
    )
    assert r2.json()["numero"] == 2
    assert Recaudo.objects.filter(numero=1).exists()


def test_transferencia_exige_soporte(api, catalogo):
    response = api.post(
        "/api/recaudos/",
        {
            "actividad": str(catalogo["actividad"].id),
            "padrino": str(catalogo["padrino"].id),
            "familia": str(catalogo["familia"].id),
            "valor": "5000",
            "medio_pago": "transferencia",
        },
        format="multipart",
    )
    assert response.status_code == 400
    assert b"comprobante" in response.content.lower()


def test_efectivo_no_acepta_soporte(api, catalogo):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    soporte = SimpleUploadedFile("comprobante.png", png, content_type="image/png")
    response = api.post(
        "/api/recaudos/",
        {
            "actividad": str(catalogo["actividad"].id),
            "padrino": str(catalogo["padrino"].id),
            "familia": str(catalogo["familia"].id),
            "valor": "5000",
            "medio_pago": "efectivo",
            "soportes": soporte,
        },
        format="multipart",
    )
    assert response.status_code == 400
    assert b"efectivo" in response.content.lower()


def test_rechaza_soporte_mayor_a_5mb():
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    grande = SimpleUploadedFile("grande.png", png, content_type="image/png")
    grande.size = 5 * 1024 * 1024 + 1
    with pytest.raises(ValidationError, match="5 MB"):
        validate_soporte(grande)


def test_rechaza_soporte_no_permitido(api, catalogo):
    exe = SimpleUploadedFile("virus.exe", b"MZ\x90\x00not-an-image", content_type="application/octet-stream")
    response = api.post(
        "/api/recaudos/",
        {
            "actividad": str(catalogo["actividad"].id),
            "padrino": str(catalogo["padrino"].id),
            "familia": str(catalogo["familia"].id),
            "valor": "5000",
            "medio_pago": "transferencia",
            "soportes": exe,
        },
        format="multipart",
    )
    assert response.status_code == 400


def test_compartir_no_afirma_envio(api, catalogo):
    creado = api.post(
        "/api/recaudos/",
        {
            "actividad": str(catalogo["actividad"].id),
            "padrino": str(catalogo["padrino"].id),
            "familia": str(catalogo["familia"].id),
            "valor": "5000",
            "medio_pago": "efectivo",
        },
        format="multipart",
    )
    recaudo_id = creado.json()["id"]
    compartir = api.get(f"/api/recaudos/{recaudo_id}/compartir/")
    body = compartir.json()
    assert "wa.me" in body["whatsapp_url"]
    assert body["tiene_telefono_familia"] is True
    assert "573019876543" in body["whatsapp_url_destino"]
    assert "no es automático" in body["aviso_whatsapp"]
    correo = api.post(
        f"/api/recaudos/{recaudo_id}/enviar-correo/",
        {"destinatario": "familia@example.com"},
        format="json",
    )
    assert correo.json()["enviado"] is False
    assert correo.json()["resultado"] == "no_configurado"

    catalogo["familia"].telefono = ""
    catalogo["familia"].save()
    sin_tel = api.get(f"/api/recaudos/{recaudo_id}/compartir/")
    assert sin_tel.json()["tiene_telefono_familia"] is False
    guardado = api.post(
        f"/api/recaudos/{recaudo_id}/telefono-familia/",
        {"telefono": "3005556677"},
        format="json",
    )
    assert guardado.status_code == 200
    assert guardado.json()["tiene_telefono_familia"] is True
    assert "573005556677" in guardado.json()["whatsapp_url_destino"]


def test_excel_export(api, catalogo):
    api.post(
        "/api/recaudos/",
        {
            "actividad": str(catalogo["actividad"].id),
            "padrino": str(catalogo["padrino"].id),
            "familia": str(catalogo["familia"].id),
            "valor": "12345.67",
            "medio_pago": "efectivo",
        },
        format="multipart",
    )
    response = api.get("/api/consultas/exportar/")
    assert response.status_code == 200
    assert "spreadsheetml" in response["Content-Type"]
    assert response.content[:2] == b"PK"


def test_importe_se_guarda_decimal(api, catalogo):
    api.post(
        "/api/recaudos/",
        {
            "actividad": str(catalogo["actividad"].id),
            "padrino": str(catalogo["padrino"].id),
            "familia": str(catalogo["familia"].id),
            "valor": "10.15",
            "medio_pago": "efectivo",
        },
        format="multipart",
    )
    recaudo = Recaudo.objects.get()
    assert recaudo.valor == Decimal("10.15")
    assert recaudo.valor == money("10.15")
    assert isinstance(recaudo.valor, Decimal)


def test_listas_vienen_paginadas(api, catalogo):
    for i in range(25):
        Familia.objects.create(
            nombre=f"Familia extra {i}",
            padrino=catalogo["padrino"],
        )
    familias = api.get("/api/familias/")
    assert familias.status_code == 200
    payload = familias.json()
    assert payload["count"] >= 26
    assert payload["page"] == 1
    assert payload["page_size"] == 20
    assert len(payload["results"]) == 20
    assert payload["pages"] >= 2

    pagina_2 = api.get("/api/familias/", {"page": 2})
    assert pagina_2.status_code == 200
    assert len(pagina_2.json()["results"]) >= 1

    recaudos = api.get("/api/recaudos/")
    assert recaudos.status_code == 200
    data = recaudos.json()
    assert "results" in data
    assert "resultados" in data
    assert "totales" in data
    assert "page" in data


def test_informes_por_actividad_padrino_fecha_y_pendientes(api, catalogo):
    otra_familia = Familia.objects.create(
        nombre="Familia López",
        padrino=catalogo["padrino"],
        telefono="3001112233",
    )
    api.post(
        "/api/recaudos/",
        {
            "actividad": str(catalogo["actividad"].id),
            "padrino": str(catalogo["padrino"].id),
            "familia": str(catalogo["familia"].id),
            "valor": "25000",
            "medio_pago": "efectivo",
            "fecha": "2026-11-10",
        },
        format="multipart",
    )
    response = api.get(
        "/api/informes/",
        {"actividad": str(catalogo["actividad"].id), "padrino": str(catalogo["padrino"].id)},
    )
    assert response.status_code == 200, response.content
    data = response.json()
    assert data["cantidad_confirmados"] == 1
    assert data["por_actividad"][0]["nombre"] == "Entrega de regalos"
    assert data["por_padrino"][0]["nombre"] == "Ana Pérez"
    assert data["por_fecha"][0]["fecha"] == "2026-11-10"
    cruzado = data["por_padrino_actividad"]
    assert len(cruzado) == 1
    assert cruzado[0]["familias_asignadas"] == 2
    assert cruzado[0]["familias_pagaron"] == 1
    assert cruzado[0]["familias_pendientes"] == 1
    pendientes = data["pendientes"]
    assert pendientes["count"] == 1
    assert pendientes["results"][0]["familia_id"] == str(otra_familia.id)
    assert pendientes["results"][0]["padrino_nombre"] == "Ana Pérez"


def test_login_requerido():
    client = APIClient()
    response = client.get("/api/padrinos/")
    assert response.status_code in (401, 403)


def test_salud_publico(client):
    response = client.get("/salud/")
    assert response.status_code == 200
    assert response.json()["estado"] == "ok"


def test_hosts_del_dominio_railway():
    from django.conf import settings

    assert ".up.railway.app" in settings.ALLOWED_HOSTS
    assert "healthcheck.railway.app" in settings.ALLOWED_HOSTS
    assert "https://*.up.railway.app" in settings.CSRF_TRUSTED_ORIGINS


def test_crud_padrino_familia_actividad(api, catalogo):
    padrino = api.post(
        "/api/padrinos/",
        {"nombre_completo": "Nuevo Padrino", "telefono": "3001112233"},
        format="json",
    )
    assert padrino.status_code == 201
    pid = padrino.json()["id"]
    editado = api.put(
        f"/api/padrinos/{pid}/",
        {"nombre_completo": "Padrino Editado", "telefono": "3001112233", "correo": "", "estado": "activo"},
        format="json",
    )
    assert editado.status_code == 200
    assert editado.json()["nombre_completo"] == "Padrino Editado"

    familia = api.post(
        "/api/familias/",
        {"nombre": "Familia Nueva", "padrino": pid, "telefono": "3009998877"},
        format="json",
    )
    assert familia.status_code == 201
    fid = familia.json()["id"]
    fam_edit = api.patch(
        f"/api/familias/{fid}/",
        {"nombre": "Familia Editada"},
        format="json",
    )
    assert fam_edit.status_code == 200
    assert fam_edit.json()["nombre"] == "Familia Editada"
    assert api.delete(f"/api/familias/{fid}/").status_code == 204
    assert not Familia.objects.filter(pk=fid).exists()

    actividad = api.post(
        "/api/actividades/",
        {
            "nombre": "Kermés",
            "fecha_inicio": "2026-01-01",
            "fecha_fin": "2026-01-31",
            "estado": "activa",
        },
        format="json",
    )
    assert actividad.status_code == 201
    aid = actividad.json()["id"]
    act_edit = api.put(
        f"/api/actividades/{aid}/",
        {
            "nombre": "Kermés 2026",
            "descripcion": "",
            "fecha_inicio": "2026-01-01",
            "fecha_fin": "2026-01-31",
            "estado": "activa",
        },
        format="json",
    )
    assert act_edit.json()["nombre"] == "Kermés 2026"
    assert api.delete(f"/api/actividades/{aid}/").status_code == 204
    assert api.delete(f"/api/padrinos/{pid}/").status_code == 204


def test_crud_pago_editar_y_eliminar(api, catalogo):
    creado = api.post(
        "/api/recaudos/",
        {
            "actividad": str(catalogo["actividad"].id),
            "padrino": str(catalogo["padrino"].id),
            "familia": str(catalogo["familia"].id),
            "valor": "10000",
            "medio_pago": "efectivo",
        },
        format="multipart",
    )
    assert creado.status_code == 201
    recaudo_id = creado.json()["id"]
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    soporte = SimpleUploadedFile("comprobante.png", png, content_type="image/png")
    editado = api.put(
        f"/api/recaudos/{recaudo_id}/",
        {
            "actividad": str(catalogo["actividad"].id),
            "padrino": str(catalogo["padrino"].id),
            "familia": str(catalogo["familia"].id),
            "valor": "25000",
            "medio_pago": "transferencia",
            "concepto": "Ajuste",
            "soportes": soporte,
        },
        format="multipart",
    )
    assert editado.status_code == 200, editado.content
    assert editado.json()["valor"] == "25000.00"
    assert editado.json()["medio_pago"] == "transferencia"
    assert len(editado.json()["soportes"]) == 1
    assert api.delete(f"/api/recaudos/{recaudo_id}/").status_code == 204
    assert not Recaudo.objects.filter(pk=recaudo_id).exists()


def test_eliminar_actividad_borra_pagos(api, catalogo):
    creado = api.post(
        "/api/recaudos/",
        {
            "actividad": str(catalogo["actividad"].id),
            "padrino": str(catalogo["padrino"].id),
            "familia": str(catalogo["familia"].id),
            "valor": "5000",
            "medio_pago": "efectivo",
        },
        format="multipart",
    )
    recaudo_id = creado.json()["id"]
    assert api.delete(f"/api/actividades/{catalogo['actividad'].id}/").status_code == 204
    assert not Recaudo.objects.filter(pk=recaudo_id).exists()
    assert not Actividad.objects.filter(pk=catalogo["actividad"].id).exists()


def test_no_elimina_padrino_con_pagos(api, catalogo):
    api.post(
        "/api/recaudos/",
        {
            "actividad": str(catalogo["actividad"].id),
            "padrino": str(catalogo["padrino"].id),
            "familia": str(catalogo["familia"].id),
            "valor": "5000",
            "medio_pago": "efectivo",
        },
        format="multipart",
    )
    response = api.delete(f"/api/padrinos/{catalogo['padrino'].id}/")
    assert response.status_code == 400
    assert Padrino.objects.filter(pk=catalogo["padrino"].id).exists()
