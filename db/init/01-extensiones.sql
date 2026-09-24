-- Extensiones de la base del sistema.
-- Se ejecuta una sola vez, cuando el contenedor inicializa un volumen de datos vacío.
-- La tabla de fragmentos usará vector(1024), la dimensión de BGE-M3.

CREATE EXTENSION IF NOT EXISTS vector;
