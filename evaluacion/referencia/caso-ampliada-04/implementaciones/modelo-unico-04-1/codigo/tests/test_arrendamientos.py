"""Pruebas de reglas, decisiones técnicas y ejemplos del cliente."""

from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone

import pytest

from arrendamientos import (
    Contrato,
    Estado,
    RepositorioMemoria,
    ServicioContratos,
)

INICIO = date(2026, 1, 1)
FIN = date(2026, 12, 31)
AHORA = datetime(2026, 1, 2, 10, tzinfo=timezone.utc)
CRUCE = "El inmueble ya tiene un contrato vigente en ese periodo"


@pytest.fixture
def sistema():
    repositorio = RepositorioMemoria()
    servicio = ServicioContratos(repositorio, reloj=lambda: AHORA)
    return servicio, repositorio


def crear(servicio, **cambios):
    datos = {
        "codigo": "C-1",
        "inmueble": "INM-100",
        "canon": 1_000_000,
        "inicio": INICIO,
        "fin": FIN,
        "usuario": "juridica",
        "identificacion_arrendatario": "AR-1",
        "documento_arrendatario": "DOC-1",
    }
    datos.update(cambios)
    return servicio.crear_borrador(**datos)


def vigente(servicio, **cambios):
    resultado = crear(servicio, **cambios)
    assert resultado.aceptado
    return servicio.activar(resultado.contrato.codigo, "activador")


def test_creacion_y_activacion_guardan_fecha_usuario_y_estado(sistema):
    servicio, repositorio = sistema
    borrador = crear(servicio)
    assert borrador.aceptado and borrador.motivo is None
    assert borrador.contrato.estado == Estado.BORRADOR
    assert borrador.contrato.historial[0].fecha == AHORA
    assert borrador.contrato.historial[0].usuario == "juridica"
    resultado = servicio.activar("C-1", "activador")
    assert resultado.aceptado
    assert resultado.contrato.estado == Estado.VIGENTE
    assert resultado.contrato.historial[-1].usuario == "activador"
    assert resultado.contrato.historial[-1].fecha == AHORA
    assert len(resultado.contrato.historial) == 2
    assert repositorio.obtener("C-1") == resultado.contrato
    assert borrador.contrato.estado == Estado.BORRADOR


def test_documento_e_identificacion_pueden_faltar_en_borrador(sistema):
    servicio, _ = sistema
    resultado = crear(
        servicio, documento_arrendatario=None, identificacion_arrendatario=None,
    )
    assert resultado.aceptado
    activado = servicio.activar(
        "C-1", "juridica", identificacion_arrendatario="AR-2",
        documento_arrendatario="DOC-2",
    )
    assert activado.aceptado
    assert activado.contrato.identificacion_arrendatario == "AR-2"
    assert activado.contrato.documento_arrendatario == "DOC-2"


@pytest.mark.parametrize(
    ("campo", "valor", "motivo"),
    [
        ("identificacion_arrendatario", None, "La identificación del arrendatario"),
        ("identificacion_arrendatario", "  ", "La identificación del arrendatario"),
        ("documento_arrendatario", None, "El documento del arrendatario"),
        ("documento_arrendatario", "", "El documento del arrendatario"),
    ],
)
def test_activacion_exige_identificacion_y_documento(sistema, campo, valor, motivo):
    servicio, repositorio = sistema
    original = crear(servicio, **{campo: valor}).contrato
    resultado = servicio.activar("C-1", "juridica")
    assert not resultado.aceptado
    assert resultado.motivo == f"{motivo} es obligatorio"
    assert resultado.contrato is None
    assert repositorio.obtener("C-1") == original


@pytest.mark.parametrize("canon", [0, -1])
def test_canon_debe_ser_positivo_al_activar(sistema, canon):
    servicio, _ = sistema
    assert crear(servicio, canon=canon).aceptado
    assert servicio.activar("C-1", "u").motivo == "El canon debe ser mayor que cero"


@pytest.mark.parametrize("fin", [INICIO, date(2025, 12, 31)])
def test_fin_debe_ser_posterior_al_inicio(sistema, fin):
    servicio, _ = sistema
    assert crear(servicio, fin=fin).aceptado
    resultado = servicio.activar("C-1", "u")
    assert resultado.motivo == "La fecha de fin debe ser posterior a la de inicio"


@pytest.mark.parametrize(
    ("inicio", "fin", "aceptado"),
    [
        (INICIO, date(2026, 6, 30), False),
        (INICIO, date(2026, 7, 1), True),
        (date(2026, 8, 31), date(2027, 2, 28), True),
        (date(2026, 8, 31), date(2027, 2, 27), False),
        (date(2023, 8, 31), date(2024, 2, 29), True),
        (date(2023, 8, 31), date(2024, 2, 28), False),
        (date(9999, 8, 1), date.max, False),
    ],
)
def test_minimo_seis_meses_calendario(sistema, inicio, fin, aceptado):
    servicio, _ = sistema
    crear(servicio, inicio=inicio, fin=fin)
    resultado = servicio.activar("C-1", "u")
    assert resultado.aceptado == aceptado
    if not aceptado:
        assert resultado.motivo == "La duración debe ser de al menos seis meses"


def test_ejemplo_cliente_nuevo_periodo_2027(sistema):
    servicio, _ = sistema
    assert vigente(servicio).aceptado
    nuevo = vigente(
        servicio, codigo="C-2", canon=1_200_000,
        inicio=date(2027, 1, 1), fin=date(2027, 12, 31),
    )
    assert nuevo.aceptado
    assert nuevo.contrato.estado == Estado.VIGENTE
    assert nuevo.contrato.canon == 1_200_000


def test_ejemplo_cliente_cruce_2026_2027(sistema):
    servicio, repositorio = sistema
    assert vigente(servicio).aceptado
    original = crear(
        servicio, codigo="C-2", canon=1_200_000,
        inicio=date(2026, 6, 1), fin=date(2027, 5, 31),
    ).contrato
    resultado = servicio.activar("C-2", "u")
    assert resultado.motivo == CRUCE
    assert repositorio.obtener("C-2") == original


@pytest.mark.parametrize(
    ("inicio", "fin"),
    [
        (date(2025, 7, 1), date(2026, 6, 1)),
        (date(2026, 2, 1), date(2026, 10, 1)),
        (date(2025, 1, 1), date(2027, 1, 1)),
        (INICIO, FIN),
    ],
)
def test_solapamientos_parciales_contenidos_e_iguales(sistema, inicio, fin):
    servicio, _ = sistema
    vigente(servicio)
    crear(servicio, codigo="C-2", inicio=inicio, fin=fin)
    assert servicio.activar("C-2", "u").motivo == CRUCE


@pytest.mark.parametrize(
    ("inicio", "fin"),
    [
        (FIN, date(2027, 12, 31)),
        (date(2025, 1, 1), INICIO),
    ],
)
def test_decision_tecnica_periodos_adyacentes_permitidos(sistema, inicio, fin):
    servicio, _ = sistema
    vigente(servicio)
    assert vigente(servicio, codigo="C-2", inicio=inicio, fin=fin).aceptado


def test_otro_inmueble_no_bloquea(sistema):
    servicio, _ = sistema
    vigente(servicio)
    assert vigente(servicio, codigo="C-2", inmueble="INM-200").aceptado


@pytest.mark.parametrize("estado", [Estado.BORRADOR, Estado.ANULADO, Estado.TERMINADO])
def test_solo_vigentes_bloquean(sistema, estado):
    servicio, repositorio = sistema
    crear(servicio)
    if estado == Estado.ANULADO:
        servicio.anular("C-1", "u")
    elif estado == Estado.TERMINADO:
        servicio.activar("C-1", "u")
        servicio.terminar("C-1", "u", "Acuerdo", date(2026, 6, 1))
    assert repositorio.vigentes("INM-100") == ()
    assert vigente(servicio, codigo="C-2").aceptado


@pytest.mark.parametrize("fecha", [INICIO, date(2026, 6, 1), FIN])
def test_terminar_exige_y_guarda_motivo_fecha_usuario(sistema, fecha):
    servicio, repositorio = sistema
    vigente(servicio)
    resultado = servicio.terminar("C-1", "abogada", "Mutuo acuerdo", fecha)
    contrato = resultado.contrato
    assert resultado.aceptado
    assert contrato.estado == Estado.TERMINADO
    assert contrato.fecha_terminacion == fecha
    assert contrato.motivo_terminacion == "Mutuo acuerdo"
    assert contrato.inicio == INICIO and contrato.fin == FIN
    assert contrato.historial[-1].fecha == AHORA
    assert contrato.historial[-1].usuario == "abogada"
    assert len(contrato.historial) == 3
    assert repositorio.obtener("C-1") == contrato


@pytest.mark.parametrize("motivo", [None, "", "  "])
def test_terminacion_sin_motivo_se_rechaza(sistema, motivo):
    servicio, repositorio = sistema
    original = vigente(servicio).contrato
    resultado = servicio.terminar("C-1", "u", motivo, INICIO)
    assert resultado.motivo == "El motivo de terminación es obligatorio"
    assert repositorio.obtener("C-1") == original


@pytest.mark.parametrize("fecha", [date(2025, 12, 31), date(2027, 1, 1)])
def test_terminacion_fuera_del_periodo_se_rechaza(sistema, fecha):
    servicio, repositorio = sistema
    original = vigente(servicio).contrato
    resultado = servicio.terminar("C-1", "u", "Acuerdo", fecha)
    assert resultado.motivo == "La fecha de terminación debe estar dentro del periodo del contrato"
    assert repositorio.obtener("C-1") == original


def test_anulacion_guarda_auditoria(sistema):
    servicio, repositorio = sistema
    crear(servicio)
    resultado = servicio.anular("C-1", "anulador")
    assert resultado.aceptado
    assert resultado.contrato.estado == Estado.ANULADO
    assert resultado.contrato.historial[-1].usuario == "anulador"
    assert resultado.contrato.historial[-1].fecha == AHORA
    assert len(resultado.contrato.historial) == 2
    assert repositorio.obtener("C-1") == resultado.contrato


@pytest.mark.parametrize(
    ("estado", "accion"),
    [
        (Estado.BORRADOR, "terminar"),
        (Estado.VIGENTE, "activar"),
        (Estado.VIGENTE, "anular"),
        (Estado.TERMINADO, "activar"),
        (Estado.TERMINADO, "terminar"),
        (Estado.TERMINADO, "anular"),
        (Estado.ANULADO, "activar"),
        (Estado.ANULADO, "terminar"),
        (Estado.ANULADO, "anular"),
    ],
)
def test_acciones_incompatibles_indican_estado_actual(sistema, estado, accion):
    servicio, repositorio = sistema
    crear(servicio)
    if estado in (Estado.VIGENTE, Estado.TERMINADO):
        servicio.activar("C-1", "u")
    if estado == Estado.TERMINADO:
        servicio.terminar("C-1", "u", "Acuerdo", INICIO)
    if estado == Estado.ANULADO:
        servicio.anular("C-1", "u")
    original = repositorio.obtener("C-1")
    if accion == "terminar":
        resultado = servicio.terminar("C-1", "u", "Acuerdo", INICIO)
    else:
        resultado = getattr(servicio, accion)("C-1", "u")
    assert resultado.motivo == f"La gestión no corresponde al estado actual: {estado.value}"
    assert repositorio.obtener("C-1") == original


def test_codigo_repetido_no_sobrescribe(sistema):
    servicio, repositorio = sistema
    original = crear(servicio).contrato
    resultado = crear(servicio, canon=2_000_000)
    assert resultado.motivo == "Ya existe un contrato con el código: C-1"
    assert repositorio.obtener("C-1") == original


@pytest.mark.parametrize("accion", ["activar", "terminar", "anular"])
def test_contrato_inexistente(sistema, accion):
    servicio, _ = sistema
    if accion == "terminar":
        resultado = servicio.terminar("NO-EXISTE", "u", "Acuerdo", INICIO)
    else:
        resultado = getattr(servicio, accion)("NO-EXISTE", "u")
    assert resultado.motivo == "No existe el contrato: NO-EXISTE"


@pytest.mark.parametrize(
    ("campo", "valor", "motivo"),
    [
        ("codigo", "", "El código del contrato es obligatorio"),
        ("codigo", 123, "El código del contrato es obligatorio"),
        ("inmueble", "  ", "El código del inmueble es obligatorio"),
        ("usuario", None, "El usuario es obligatorio"),
        ("canon", 1.5, "El canon debe ser un número entero de pesos"),
        ("canon", 1_000_000.0, "El canon debe ser un número entero de pesos"),
        ("canon", True, "El canon debe ser un número entero de pesos"),
        ("canon", "1000000", "El canon debe ser un número entero de pesos"),
        ("inicio", "2026-01-01", "La fecha de inicio debe ser una fecha de calendario"),
        ("fin", None, "La fecha de fin debe ser una fecha de calendario"),
        ("inicio", AHORA, "La fecha de inicio debe ser una fecha de calendario"),
        (
            "identificacion_arrendatario", 123,
            "La identificación del arrendatario debe ser texto o None",
        ),
        ("documento_arrendatario", 123, "El documento del arrendatario debe ser texto o None"),
    ],
)
def test_datos_de_creacion_invalidos(sistema, campo, valor, motivo):
    servicio, repositorio = sistema
    resultado = crear(servicio, **{campo: valor})
    assert resultado.motivo == motivo
    assert repositorio.obtener("C-1") is None


@pytest.mark.parametrize("accion", ["activar", "terminar", "anular"])
def test_todo_cambio_exige_usuario(sistema, accion):
    servicio, repositorio = sistema
    crear(servicio)
    if accion == "terminar":
        servicio.activar("C-1", "u")
    original = repositorio.obtener("C-1")
    if accion == "terminar":
        resultado = servicio.terminar("C-1", " ", "Acuerdo", INICIO)
    else:
        resultado = getattr(servicio, accion)("C-1", " ")
    assert resultado.motivo == "El usuario es obligatorio"
    assert repositorio.obtener("C-1") == original


@pytest.mark.parametrize("accion", ["activar", "terminar", "anular"])
def test_codigo_vacio_en_gestiones(sistema, accion):
    servicio, _ = sistema
    if accion == "terminar":
        resultado = servicio.terminar("", "u", "Acuerdo", INICIO)
    else:
        resultado = getattr(servicio, accion)("", "u")
    assert resultado.motivo == "El código del contrato es obligatorio"


@pytest.mark.parametrize("fecha", [None, "2026-06-01", AHORA])
def test_formato_fecha_terminacion(sistema, fecha):
    servicio, _ = sistema
    vigente(servicio)
    resultado = servicio.terminar("C-1", "u", "Acuerdo", fecha)
    assert resultado.motivo == "La fecha de terminación debe ser una fecha de calendario"


@pytest.mark.parametrize("campo", ["identificacion_arrendatario", "documento_arrendatario"])
def test_datos_aportados_al_activar_invalidos_no_se_guardan(sistema, campo):
    servicio, repositorio = sistema
    original = crear(servicio).contrato
    resultado = servicio.activar("C-1", "u", **{campo: 123})
    assert not resultado.aceptado
    assert "debe ser texto o None" in resultado.motivo
    assert repositorio.obtener("C-1") == original


def test_activacion_rechazada_no_guarda_datos_aportados(sistema):
    servicio, repositorio = sistema
    original = crear(servicio, canon=0, documento_arrendatario=None).contrato
    resultado = servicio.activar("C-1", "u", documento_arrendatario="NUEVO")
    assert not resultado.aceptado
    assert repositorio.obtener("C-1") == original
    assert original.documento_arrendatario is None


def test_reloj_se_consulta_por_cambio_exitoso():
    instantes = iter([
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 2, tzinfo=timezone.utc),
        datetime(2026, 1, 3, tzinfo=timezone.utc),
    ])
    servicio = ServicioContratos(RepositorioMemoria(), reloj=lambda: next(instantes))
    crear(servicio, documento_arrendatario=None)
    assert not servicio.activar("C-1", "u").aceptado
    resultado = servicio.activar("C-1", "u", documento_arrendatario="DOC")
    assert [c.fecha.day for c in resultado.contrato.historial] == [1, 2]
    resultado = servicio.terminar("C-1", "u", "Acuerdo", INICIO)
    assert [c.fecha.day for c in resultado.contrato.historial] == [1, 2, 3]


def test_contrato_e_historial_inmutables(sistema):
    servicio, repositorio = sistema
    contrato = crear(servicio).contrato
    with pytest.raises(FrozenInstanceError):
        contrato.canon = 0
    with pytest.raises(FrozenInstanceError):
        contrato.historial[0].usuario = "otro"
    assert repositorio.obtener("C-1").canon == 1_000_000
    assert isinstance(contrato.historial, tuple)


class AlmacenAlternativo:
    def __init__(self):
        self.datos = []

    def obtener(self, codigo):
        return next((c for c in self.datos if c.codigo == codigo), None)

    def guardar(self, contrato):
        self.datos = [c for c in self.datos if c.codigo != contrato.codigo]
        self.datos.append(contrato)

    def vigentes(self, inmueble):
        return tuple(
            c for c in self.datos if c.inmueble == inmueble and c.estado == Estado.VIGENTE
        )


def test_reglas_funcionan_con_otro_almacenamiento():
    almacen = AlmacenAlternativo()
    servicio = ServicioContratos(almacen, reloj=lambda: AHORA)
    assert vigente(servicio).aceptado
    crear(servicio, codigo="C-2")
    assert servicio.activar("C-2", "u").motivo == CRUCE
    assert isinstance(almacen.obtener("C-1"), Contrato)
    assert almacen.obtener("C-2").estado == Estado.BORRADOR


def test_reloj_predeterminado_registra_datetime_utc():
    servicio = ServicioContratos(RepositorioMemoria())
    resultado = crear(servicio)
    assert resultado.contrato.historial[0].fecha.tzinfo == timezone.utc
