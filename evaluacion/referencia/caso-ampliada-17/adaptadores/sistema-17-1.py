"""Adaptador de sistema-17-1: arma el canal en memoria, los consumidores y los almacenes.

Esta versión pide registrar aparte la fecha de radicación: es la del primer aviso de cada trámite.
"""

from datetime import datetime

from consumidores.bitacora import BitacoraConsumidor
from consumidores.indicador import IndicadorConsumidor
from consumidores.mensajes import MensajesConsumidor
from infraestructura.bitacora_memoria import RegistroBitacoraMemoria
from infraestructura.calendario_tramite_memoria import RegistroFechasTramiteMemoria
from infraestructura.canal_memoria import CanalEventosMemoria
from infraestructura.indicadores_memoria import RegistroIndicadoresMemoria
from infraestructura.mensajes_memoria import RegistroMensajesMemoria
from productores.cambios_estado import publicar_cambio_estado


def procesar(
    avisos: list[dict[str, object]],
) -> tuple[list[tuple[str, bool]], list[str], dict[str, float]]:
    canal = CanalEventosMemoria()
    bitacora = RegistroBitacoraMemoria()
    indicadores = RegistroIndicadoresMemoria()
    fechas = RegistroFechasTramiteMemoria()
    mensajes = RegistroMensajesMemoria()
    canal.suscribir(BitacoraConsumidor(bitacora).manejar)
    canal.suscribir(IndicadorConsumidor(indicadores, fechas).manejar)
    canal.suscribir(MensajesConsumidor(mensajes).manejar)
    numeros: list[str] = []
    tipos: list[str] = []
    for aviso in avisos:
        fecha: datetime = aviso["fecha"]
        if aviso["numero"] not in numeros:
            numeros.append(aviso["numero"])
            fechas.registrar_radicado(aviso["numero"], fecha.date())
        if aviso["tipo"] not in tipos:
            tipos.append(aviso["tipo"])
        publicar_cambio_estado(
            canal,
            aviso["numero"],
            aviso["tipo"],
            aviso["estado_anterior"],
            aviso["estado_nuevo"],
            fecha,
            aviso["funcionario"],
        )
        canal.despachar_pendientes()
    registro = [
        (asiento.numero_tramite, asiento.transicion_valida)
        for numero in numeros
        for asiento in bitacora.consultar_por_tramite(numero)
    ]
    textos = [m.texto for numero in numeros for m in mensajes.consultar_por_tramite(numero)]
    return registro, textos, {tipo: indicadores.promedio_por_tipo(tipo) for tipo in tipos}
