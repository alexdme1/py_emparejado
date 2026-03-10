# 🌸 py_emparejado

Aplicación web local para **emparejar visualmente imágenes frontales y traseras** de vehículos. Usa Flask + una interfaz web oscura con atajos de teclado para un flujo de trabajo rápido.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0+-green?logo=flask)

## 📋 ¿Qué hace?

1. **`app.py`** — Servidor web Flask que muestra pares de imágenes (frontal/trasera) lado a lado. Permite emparejarlas, descartarlas o navegar entre candidatas usando teclado.
2. **`rename_pairs.py`** — Renombra las parejas creadas al formato `1F.png / 1B.png`, aplicando rotación y flip automáticos.
3. **`flatten_dataset.py`** — Mueve todas las imágenes de las subcarpetas a una única carpeta `dataset_final/`.

## 🚀 Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/alexdme1/py_emparejado.git
cd py_emparejado

# 2. Crear entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt
```

## 📂 Estructura de carpetas

Antes de ejecutar, coloca tus imágenes en las carpetas correspondientes:

```
py_emparejado/
├── frontales/          ← Imágenes frontales aquí
├── traseras/           ← Imágenes traseras aquí
├── paired_images/      ← Se genera automáticamente (parejas)
├── dataset_final/      ← Se genera con flatten_dataset.py
├── templates/
│   └── index.html      ← Interfaz web
├── app.py              ← Servidor principal
├── rename_pairs.py     ← Renombrado de parejas
├── flatten_dataset.py  ← Aplanar dataset
├── requirements.txt
└── README.md
```

## ▶️ Uso

### 1. Emparejar imágenes

```bash
python app.py
```

Abre el navegador en **http://localhost:5000** y empareja las imágenes:

| Tecla | Acción |
|-------|--------|
| `Enter` | ✓ Marcar como pareja |
| `D` / `→` | Siguiente trasera |
| `A` / `←` | Trasera anterior |
| `S` | Marcar frontal sin pareja |
| `W` | Marcar trasera sin pareja |
| `Z` | Deshacer última acción |

### 2. Renombrar parejas

```bash
python rename_pairs.py
# Opciones:
#   --input carpeta_entrada
#   --output carpeta_salida
#   --dry-run  (solo muestra, no modifica)
```

### 3. Aplanar dataset

```bash
python flatten_dataset.py
```

Mueve todas las imágenes de `paired_images/` a `dataset_final/` en una sola carpeta plana.

## 📝 Notas

- Las carpetas `frontales/`, `traseras/`, `dataset_final/` y `paired_images/` están en `.gitignore` porque contienen imágenes pesadas.
- El archivo `state.json` se genera automáticamente al iniciar la app y guarda el progreso de la sesión.
- Al clonar el repo en otro PC, solo necesitas colocar tus imágenes en `frontales/` y `traseras/` y ejecutar `app.py`.
