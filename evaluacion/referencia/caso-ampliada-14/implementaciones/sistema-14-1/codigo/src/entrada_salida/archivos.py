"""Adaptador de operaciones sobre carpetas y archivos locales."""

from builtins import FileNotFoundError as CarpetaNoExiste
from pathlib import Path


class GestorArchivos:
    """Accede al sistema de archivos sin mantener estado compartido."""

    def crear_carpeta(self, ruta: str) -> None:
        """Crea una carpeta y sus padres si es necesario.

        Args:
            ruta: Ruta de la carpeta.
        """
        Path(ruta).mkdir(parents=True, exist_ok=True)

    def crear_archivo(self, ruta: str, nombre: str, contenido: bytes | None) -> None:
        """Crea un archivo dentro de la carpeta indicada.

        Args:
            ruta: Carpeta de destino.
            nombre: Nombre del archivo, sin componentes de ruta.
            contenido: Contenido binario; None crea un archivo vacío.

        Raises:
            ValueError: El nombre contiene componentes de ruta.
            CarpetaNoExiste: La carpeta no existe.
        """
        self._comprobar_carpeta(ruta)
        self._comprobar_nombre(nombre)
        (Path(ruta) / nombre).write_bytes(b"" if contenido is None else contenido)

    def existe_carpeta(self, ruta: str) -> bool:
        """Indica si la ruta identifica una carpeta existente.

        Args:
            ruta: Ruta que se consulta.

        Returns:
            True si la carpeta existe, False en caso contrario.
        """
        return isinstance(ruta, str) and bool(ruta.strip()) and Path(ruta).is_dir()

    def listar_archivos(self, ruta: str) -> list[str]:
        """Lista los archivos inmediatos, en orden alfabético.

        Args:
            ruta: Carpeta que se consulta.

        Returns:
            Nombres de archivos, sin incluir subcarpetas.

        Raises:
            CarpetaNoExiste: La carpeta no existe.
        """
        self._comprobar_carpeta(ruta)
        return sorted(entrada.name for entrada in Path(ruta).iterdir() if entrada.is_file())

    def renombrar(self, ruta: str, nombre_anterior: str, nombre_nuevo: str) -> None:
        """Renombra un archivo sin sobrescribir un destino existente.

        Args:
            ruta: Carpeta que contiene el archivo.
            nombre_anterior: Nombre original, sin ruta.
            nombre_nuevo: Nombre de destino, sin ruta.

        Raises:
            CarpetaNoExiste: La carpeta no existe.
            ValueError: Un nombre contiene componentes de ruta.
            FileExistsError: El destino ya existe.
        """
        self._comprobar_carpeta(ruta)
        self._comprobar_nombre(nombre_anterior)
        self._comprobar_nombre(nombre_nuevo)
        origen = Path(ruta) / nombre_anterior
        destino = Path(ruta) / nombre_nuevo
        if nombre_anterior == nombre_nuevo:
            return
        if destino.exists():
            raise FileExistsError("Conflicto")
        origen.rename(destino)

    def _comprobar_carpeta(self, ruta: str) -> None:
        if not self.existe_carpeta(ruta):
            raise CarpetaNoExiste(f"La carpeta no existe: {ruta}")

    @staticmethod
    def _comprobar_nombre(nombre: str) -> None:
        if not isinstance(nombre, str) or nombre in ("", ".", ".."):
            raise ValueError("El nombre de archivo no es válido")
        if "/" in nombre or "\\" in nombre or "\x00" in nombre:
            raise ValueError("El nombre debe identificar un archivo dentro de la carpeta")
