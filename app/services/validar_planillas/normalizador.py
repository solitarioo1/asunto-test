import re
import unicodedata


def _quitar_tildes(texto: str) -> str:
    forma_nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in forma_nfkd if not unicodedata.combining(c))


def normalizar_nombre(nombre: str) -> str:
    """Mayúsculas, sin tildes, sin puntuación, palabras ordenadas alfabéticamente —
    para que "GARCÍA LÓPEZ, JUAN" y "JUAN GARCIA LOPEZ" se reconozcan como la misma persona."""
    sin_tildes = _quitar_tildes(nombre).upper()
    sin_puntuacion = re.sub(r"[^\w\s]", " ", sin_tildes)
    palabras = sorted(sin_puntuacion.split())
    return " ".join(palabras)
