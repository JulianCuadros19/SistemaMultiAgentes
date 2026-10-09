# Registro de solicitudes de mutación

Valida los datos de RF-01, verifica la existencia del predio, obtiene el radicado y guarda una solicitud en estado `en trámite`. Los tres módulos son paquetes de espacio de nombres; agregue `src` al camino de importación. No se necesita ninguna dependencia externa en producción.

## Registro desde presentación

```python
from datetime import date
from presentacion.registro_mutacion import registrar_solicitud_mutacion

solicitudes = []
predios = {"1" * 30}

solicitud = registrar_solicitud_mutacion(
    numero_predial="1" * 30,
    tipo_documento_soporte="escritura pública",
    fecha_documento_soporte=date(2026, 1, 1),
    identificacion_nuevo_propietario="123456",
    nombre_completo_nuevo_propietario="Persona de prueba",
    generar_radicado=lambda fecha: f"RAD-{fecha.year:04d}-000123",
    predio_existe=lambda numero: numero in predios,
    guardar_solicitud=solicitudes.append,
    fecha_radicacion=date(2026, 1, 2),
)
```

La función de `aplicacion.registro_mutacion` tiene exactamente los mismos argumentos y resultado. Para utilizar directamente el caso de uso, sustituya la importación anterior por:

```python
from aplicacion.registro_mutacion import registrar_solicitud_mutacion
```

La presentación delega las validaciones al caso de uso, sin duplicarlas. Los colaboradores se invocan únicamente después de validar las entradas. Una identificación inválida no consulta el predio, no consume un radicado ni guarda una solicitud. Un predio inexistente no consume un radicado ni guarda una solicitud. Un radicado inválido tampoco se guarda. Los errores de los colaboradores se propagan sin ocultarlos.

## Entidad y validadores

```python
from datetime import date
from dominio.solicitud import (
    SolicitudMutacion,
    validar_fecha_documento_no_posterior,
    validar_tipo_documento,
)

validar_tipo_documento("sentencia judicial")
validar_fecha_documento_no_posterior(date(2026, 1, 2), date(2026, 1, 2))

solicitud = SolicitudMutacion(
    "1" * 30,
    "sentencia judicial",
    date(2026, 1, 2),
    "123456",
    "Persona de prueba",
    date(2026, 1, 2),
    "RAD-2026-000123",
    "en trámite",
)
```

Los validadores retornan `None` si el dato es válido. La entidad es inmutable y verifica las invariantes locales, incluida la identificación, pero no consulta la existencia del predio: esa comprobación corresponde al caso de uso.

## Excepciones y supuestos

- `PredioInexistente`: número predial mal formado o ausente de la base catastral. Se requieren exactamente 30 dígitos ASCII, conservando los ceros iniciales.
- `TipoDocumentoInvalido`: tipo de soporte no permitido. Al no existir excepciones específicas para otros datos textuales, también se utiliza para identificación inválida, textos obligatorios ausentes, radicado o estado inválidos y colaboradores no invocables.
- La identificación debe ser texto con entre 6 y 10 dígitos ASCII, sin espacios, signos ni letras. Se conservan los ceros iniciales. En caso de rechazo se informa: «La identificación del nuevo propietario debe contener solo dígitos, entre 6 y 10.»
- `FechaDocumentoInvalida`: fechas ausentes, de tipo incorrecto o documento posterior a la radicación. Se aceptan objetos `date`, no `datetime`.
- El nombre obligatorio debe contener al menos un carácter no blanco; no se modifica ni se aplican restricciones adicionales.
- Se acepta igualdad de fechas para ambos tipos documentales, conforme a la regla general «no posterior»; no se añade una prohibición para escrituras públicas.
- Si se omite `fecha_radicacion`, se utiliza `date.today()` una sola vez. Para resultados deterministas, proporcione la fecha explícitamente.
- La unicidad y asignación del consecutivo son responsabilidad de `generar_radicado`. Se valida el formato y la correspondencia del año con la fecha de radicación. No se impone un inicio del consecutivo no especificado.
- La lógica no accede a red, archivos ni bases de datos; las consultas y persistencia son colaboradores inyectados.

## Pruebas

Con `src` en el camino de importación, ejecute `pytest tests/test_registro_mutacion.py`. Las pruebas cubren ESC-01, ESC-02 y ESC-03, entradas inválidas, ausencia de efectos ante rechazo y límites de fechas, longitud predial, identificación y formato del radicado.
