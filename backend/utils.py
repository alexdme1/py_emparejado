"""
Utilidades compartidas del backend.
"""
import os
from backend.config import IMAGE_EXTENSIONS


def get_sorted_images(directory):
    """Lista ordenada de imágenes en un directorio."""
    if not os.path.isdir(directory):
        return []
    return sorted(
        f for f in os.listdir(directory)
        if f.lower().endswith(IMAGE_EXTENSIONS)
    )
