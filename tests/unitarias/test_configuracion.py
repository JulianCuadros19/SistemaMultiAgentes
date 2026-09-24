"""Pruebas de la configuración de base de datos sin depender del entorno ni de .env."""

from psycopg.conninfo import conninfo_to_dict

from multiagente.core.configuracion import ConfiguracionBaseDatos

CONTRASENA = "clave con espacios y 'comillas'"


def construir() -> ConfiguracionBaseDatos:
    return ConfiguracionBaseDatos(
        _env_file=None,
        host="servidor",
        port=5433,
        db="pruebas",
        user="usuario",
        password=CONTRASENA,
    )


def test_cadena_conexion_contiene_todos_los_parametros():
    partes = conninfo_to_dict(construir().cadena_conexion())
    assert partes == {
        "host": "servidor",
        "port": "5433",
        "dbname": "pruebas",
        "user": "usuario",
        "password": CONTRASENA,
    }


def test_contrasena_no_aparece_en_la_representacion():
    configuracion = construir()
    assert CONTRASENA not in repr(configuracion)
    assert CONTRASENA not in str(configuracion)
