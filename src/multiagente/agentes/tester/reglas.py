"""Reglas de calidad del tester, leídas de la base de conocimiento como fuente única.

N12 y N14 citan en cada hallazgo la regla que lo origina, con la severidad que la regla declara
(cal-sv, conducta 4). Las reglas se leen de los archivos de `criterios_calidad`, igual que el
arquitecto lee su catálogo: la severidad no se copia en el código.

Este módulo también fija cómo se verifica cada regla de forma automática: la regla de cada código
de Ruff y la sugerencia de corrección de cada regla. Las reglas sin comprobación automática se
declaran como no evaluadas (cal-sv, conducta 5).
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from multiagente.orquestador.estado import Severidad
from multiagente.rag.colecciones import Coleccion
from multiagente.rag.documentos import RAIZ_CONOCIMIENTO, cargar_corpus
from multiagente.rag.segmentacion import segmentar

REGLA_ESTILO = "CAL-MT-009"
"""Regla de las infracciones de estilo que no corresponden a otra regla."""

REGLAS_RUFF: tuple[tuple[str, str], ...] = (
    ("S102", "CAL-SG-002"),
    ("S307", "CAL-SG-002"),
    ("S608", "CAL-SG-003"),
    ("S60", "CAL-SG-004"),
    ("S110", "CAL-SG-006"),
    ("S112", "CAL-SG-006"),
    ("BLE", "CAL-SG-006"),
    ("S311", "CAL-SG-008"),
    ("B006", "CAL-FB-002"),
    ("B008", "CAL-FB-002"),
    ("C901", "CAL-MT-003"),
    ("F401", "CAL-MT-004"),
    ("F811", "CAL-MT-004"),
    ("F841", "CAL-MT-004"),
    ("ANN", "CAL-MT-002"),
    ("D", "CAL-MT-001"),
    ("N", "CAL-MT-007"),
)
"""Prefijo de código de Ruff y regla que lo verifica; gana el prefijo más largo. Un código sin
prefijo en la tabla se reporta con la regla de estilo (CAL-MT-009). Los secretos (S105, S106 y
S107) no están: la configuración del código generado los ignora y CAL-SG-001 la verifica N12."""

EVALUADAS: frozenset[str] = frozenset(
    {regla for _, regla in REGLAS_RUFF}
    | {REGLA_ESTILO}
    | {"CAL-AR-001", "CAL-AR-002", "CAL-AR-003", "CAL-AR-004", "CAL-AR-005"}
    | {"CAL-MT-005", "CAL-MT-006", "CAL-MT-008", "CAL-MT-010"}
    | {"CAL-FS-001", "CAL-FS-002", "CAL-FS-003", "CAL-FS-005", "CAL-FS-006"}
    | {"CAL-SG-001"}
)
"""Reglas con comprobación automática. CAL-MT-005 se verifica con CAL-AR-001 y CAL-AR-003,
CAL-MT-008 al ejecutar las pruebas de dominio en el entorno aislado, que no tiene red, y
CAL-SG-001 con el detector de secretos de N12."""

SUGERENCIAS: dict[str, str] = {
    "CAL-AR-001": "Crea el módulo en la ruta que declara la especificación.",
    "CAL-AR-002": "Ajusta la interfaz a la firma declarada: mismos parámetros, tipos y retorno, "
    "y define o importa las excepciones declaradas.",
    "CAL-AR-003": "Elimina el archivo o mueve su contenido a un módulo declarado.",
    "CAL-AR-004": "Usa solo las dependencias externas que declara la especificación.",
    "CAL-AR-005": "Agrega una prueba test_rf_NN_… que importe y ejercite un módulo asignado al "
    "requerimiento.",
    "CAL-FB-002": "Usa None como valor por defecto y crea el objeto dentro de la función.",
    "CAL-FS-001": "Escribe una prueba test_rf_NN_esc_NN_… que prepare el «dado que», ejecute el "
    "«cuando» y verifique exactamente el «entonces» del escenario.",
    "CAL-FS-002": "Corrige el código para que la prueba pase sin debilitar lo que verifica.",
    "CAL-FS-003": "Corrige el error para que el módulo se pueda importar.",
    "CAL-FS-005": "Usa decimal.Decimal, construido desde str o int, en todo valor monetario o "
    "de avalúo.",
    "CAL-FS-006": "Prepara la situación con las interfaces públicas del módulo y verifica lo que "
    "él devuelve o deja registrado; no inyectes atributos ni lances tú la excepción esperada.",
    "CAL-MT-001": "Agrega un docstring al estilo Google con Args, Returns y Raises.",
    "CAL-MT-002": "Anota el tipo de cada parámetro y del valor de retorno.",
    "CAL-MT-003": "Divide la función en funciones más pequeñas hasta bajar del umbral de "
    "complejidad.",
    "CAL-MT-004": "Elimina la importación, la variable o la definición que no se usa.",
    "CAL-MT-006": "Importa solo módulos declarados de las dependencias permitidas, con ruta "
    "absoluta, o mueve la lógica al módulo que corresponde.",
    "CAL-MT-007": "Renombra con snake_case las funciones y variables y con PascalCase las clases.",
    "CAL-MT-009": "Ajusta el código a la configuración de estilo del sistema.",
    "CAL-MT-010": "Haz público el nombre en su módulo o deja esa lógica dentro de él.",
    "CAL-SG-001": "Lee el secreto de la configuración o del entorno; no lo escribas en el código.",
    "CAL-SG-002": "Elimina eval y exec; interpreta los datos con un análisis explícito.",
    "CAL-SG-003": "Construye la consulta con parámetros vinculados.",
    "CAL-SG-004": "No invoques procesos del sistema desde el módulo.",
    "CAL-SG-006": "Captura la excepción concreta y trátala o regístrala; no la silencies.",
    "CAL-SG-008": "Usa el módulo secrets para valores con propósito de seguridad.",
}
"""Sugerencia de corrección para el desarrollador por cada regla con comprobación automática."""


class ErrorReglas(ValueError):
    """La base de conocimiento no tiene las reglas de calidad en la forma esperada."""


@dataclass(frozen=True)
class ReglaCalidad:
    """Regla de calidad atómica de la base de conocimiento (`### REGLA`)."""

    id: str
    nombre: str
    severidad: Severidad
    caracteristica: str
    norma: str
    documento: str


def cargar_reglas_calidad(raiz: Path = RAIZ_CONOCIMIENTO) -> dict[str, ReglaCalidad]:
    """Lee las reglas de la colección `criterios_calidad` con su severidad.

    Args:
        raiz: Carpeta raíz de la base de conocimiento.

    Returns:
        Las reglas por identificador, p. ej. `CAL-MT-001`.

    Raises:
        ErrorReglas: Si una regla declara una severidad desconocida, si falta una regla con
            comprobación automática o si alguna no tiene sugerencia.
    """
    reglas: dict[str, ReglaCalidad] = {}
    for documento in cargar_corpus(raiz):
        if documento.metadatos.coleccion is not Coleccion.CRITERIOS_CALIDAD:
            continue
        for fragmento in segmentar(documento):
            datos = fragmento.metadatos
            if "regla" not in datos:
                continue
            try:
                severidad = Severidad(datos["severidad"].strip().lower())
            except (KeyError, ValueError) as error:
                raise ErrorReglas(f"{datos['regla']}: severidad inválida") from error
            reglas[datos["regla"]] = ReglaCalidad(
                id=datos["regla"],
                nombre=datos["nombre"],
                severidad=severidad,
                caracteristica=datos.get("caracteristica", ""),
                norma=datos.get("norma", ""),
                documento=documento.metadatos.id,
            )
    if faltantes := sorted(EVALUADAS - set(reglas)):
        raise ErrorReglas(f"Faltan en la base de conocimiento las reglas {faltantes}")
    if sin_sugerencia := sorted(EVALUADAS - set(SUGERENCIAS) - {"CAL-MT-005", "CAL-MT-008"}):
        raise ErrorReglas(f"Reglas sin sugerencia de corrección: {sin_sugerencia}")
    return reglas


def regla_de_ruff(codigo: str) -> str:
    """Regla de calidad que verifica un código de Ruff.

    Args:
        codigo: Código de la infracción, p. ej. `S307` o `E501`.

    Returns:
        La regla del prefijo más largo que coincide, o la de estilo si ninguno coincide.
    """
    candidatos = [(prefijo, regla) for prefijo, regla in REGLAS_RUFF if codigo.startswith(prefijo)]
    if not candidatos:
        return REGLA_ESTILO
    return max(candidatos, key=lambda candidato: len(candidato[0]))[1]


def estilo_bloqueante(
    reglas: dict[str, ReglaCalidad], umbral_media: int
) -> Callable[[str], str | None]:
    """Criterio con que un código de Ruff rechaza la versión, según la regla de cal-sv.

    Una regla de severidad alta rechaza siempre; una media, si el umbral de hallazgos medios es
    cero. N10 lo recibe para que su reintento corrija esas infracciones antes del tester, que
    sigue siendo quien dictamina (ADR-0015).

    Args:
        reglas: Reglas de calidad leídas de la base.
        umbral_media: Hallazgos de severidad media que admite el veredicto.

    Returns:
        Función que da la regla de un código de Ruff si su infracción rechaza la versión, o None.
    """

    def regla(codigo: str) -> str | None:
        id_regla = regla_de_ruff(codigo)
        severidad = reglas[id_regla].severidad
        if severidad is Severidad.ALTA or (severidad is Severidad.MEDIA and umbral_media == 0):
            return id_regla
        return None

    return regla
