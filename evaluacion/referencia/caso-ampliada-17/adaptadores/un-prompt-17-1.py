"""Adaptador de un-prompt-17-1: usa su `SistemaAvisos`, que pide la fecha de radicación aparte.

La fecha de radicación es la del primer aviso de cada trámite.
"""

from avisos_catastrales.modulo import Aviso, Estado, SistemaAvisos, TipoTramite


def procesar(
    avisos: list[dict[str, object]],
) -> tuple[list[tuple[str, bool]], list[str], dict[str, float]]:
    sistema = SistemaAvisos()
    numeros: set[str] = set()
    for aviso in avisos:
        if aviso["numero"] not in numeros:
            numeros.add(aviso["numero"])
            sistema.indicador.registrar_radicacion(aviso["numero"], aviso["fecha"].date())
        sistema.canal.publicar(
            Aviso(
                aviso["numero"],
                TipoTramite(aviso["tipo"]),
                Estado(aviso["estado_anterior"]),
                Estado(aviso["estado_nuevo"]),
                aviso["fecha"],
                aviso["funcionario"],
            )
        )
    sistema.canal.esperar()
    bitacora = [(r.aviso.numero, r.valido) for r in sistema.bitacora.registros]
    mensajes = [m.texto for m in sistema.mensajes.mensajes]
    promedios = {tipo.value: dias for tipo, dias in sistema.indicador.promedios.items()}
    sistema.cerrar()
    return bitacora, mensajes, promedios
