"""
Configuración central de la aplicación.
"""
import os

# Directorio raíz del proyecto
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Defaults para Roboflow ──
ROBOFLOW_WORKSPACE = "floresverdnatura"
ROBOFLOW_PROJECT = "proyecto_h_clas"
ROBOFLOW_BATCH_PREFIX = "crops"

# ── Categorías de cropping por defecto ──
DEFAULT_CATEGORIES = ["Flores", "Planta"]

# ── IDs de categoría a excluir (superclases duplicadas de Roboflow) ──
EXCLUDE_CATEGORY_IDS = {0}

# ── Splits de Roboflow a procesar ──
DEFAULT_SPLITS = ["train"]

# ── Tamaño mínimo de crop ──
MIN_CROP_SIZE = 1

# ── Extensiones de imágenes aceptadas ──
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff')

# ── Google Drive ──
# Último índice de emparejado existente en Drive
DRIVE_LAST_INDEX = 535

# ── Emparejado ──
DEFAULT_TIME_WINDOW = 120  # segundos para ventana de candidatas

# ── Rutas del frontend build ──
FRONTEND_DIST = os.path.join(PROJECT_ROOT, 'frontend', 'dist')
