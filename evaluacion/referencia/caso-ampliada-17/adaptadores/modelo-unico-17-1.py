"""Adaptador de modelo-unico-17-1: usa su `Sistema`, que pide la fecha de radicación aparte.

La fecha de radicación es la del primer aviso de cada trámite.
"""

from avisos_catastrales import Aviso, Sistema


def procesar(
    avisos: list[dict[str, object]],
) -> tuple[list[tuple[str, bool]], list[str], dict[str, float]]:
    sistema = Sistema()
    numeros: set[str] = set()
    for aviso in avisos:
        if aviso["numero"] not in numeros:
            numeros.add(aviso["numero"])
            sistema.indicador.guardar_fecha_radicacion(aviso["numero"], aviso["fecha"].date())
        sistema.publicar(
            Aviso(
                aviso["numero"],
                aviso["tipo"],
                aviso["estado_anterior"],
                aviso["estado_nuevo"],
                aviso["fecha"],
                aviso["funcionario"],
            )
        )
    sistema.esperar()
    bitacora = [(r.aviso.numero, r.valida) for r in sistema.bitacora.registros]
    mensajes = [m.texto for m in sistema.mensajes.mensajes]
    promedios = sistema.indicador.promedios
    sistema.cerrar()
    return bitacora, mensajes, promedios
