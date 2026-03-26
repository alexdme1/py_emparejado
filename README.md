# Image Toolkit 🖼️

Herramienta web local para procesamiento de imágenes con tres módulos:

- **✂️ Cropear** — Recorte automático de imágenes desde exports COCO de Roboflow + subida automática.
- **🔗 Emparejar** — Emparejado visual de imágenes frontales/traseras con renombrado y subida a Google Drive.
- **🏷️ Etiquetar** — Verificación manual y conteo real de unidades para entrenar el Árbol de Decisión.
- **🧪 Testing** — Prueba integral de los modelos (Mask R-CNN, ConvNeXt, Árbol) con la tubería completa.
- **📹 Extraer de Vídeo** — Extrae capturas de vídeos de cámaras de seguridad usando YOLOv8n para detección de personas.

---

## Requisitos

- **Python 3.10+** con pip

> Node.js NO es necesario para usar la app — el frontend viene pre-compilado.
> Solo hace falta si quieres modificar el frontend.

---

## Instalación en Windows

Abre **CMD** o **PowerShell** y ejecuta estos comandos uno a uno:

```cmd
git clone https://github.com/alexdme1/py_emparejado.git

cd py_emparejado

python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

python run.py
```

Se abrirá el navegador automáticamente en `http://localhost:5000`.

> **Nota**: La primera vez que uses el módulo de vídeo, YOLOv8n se descargará automáticamente (~6 MB).

---

## Instalación en Linux / Mac

```bash
git clone https://github.com/alexdme1/py_emparejado.git
cd py_emparejado
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

---

## Uso

```bash
python run.py
```

| Flag            | Descripción                               |
|-----------------|-------------------------------------------|
| `--port 8080`   | Puerto personalizado                      |
| `--no-browser`  | No abrir el navegador automáticamente     |
| `--dev`         | Modo desarrollo (solo backend)            |
| `--build`       | Forzar rebuild del frontend (necesita Node.js) |

---

## Módulos

### ✂️ Cropping
1. Selecciona la carpeta del export COCO de Roboflow
2. Elige categorías a recortar (por defecto: Flores, Planta)
3. Configura tu API key y proyecto de Roboflow
4. Ejecuta → los crops se generan y suben automáticamente

### 🔗 Emparejado
1. Selecciona carpetas de frontales, traseras y salida
2. Empareja visualmente con atajos de teclado:
   - `Enter` — Es pareja
   - `D` / `→` — Siguiente trasera
   - `A` / `←` — Anterior trasera
   - `S` — Frontal sin pareja
   - `W` — Trasera sin pareja
   - `Z` — Deshacer
3. Al terminar: **Renombrar Parejas** (formato NF/NB)
4. **Subir a Google Drive** (numeración continua)

### 🏷️ Etiquetado (Árbol de Decisión)
1. Carga las inferencias en `data/arbol_conteo/detections_raw.csv`
2. En la pestaña de Etiquetado, visualizarás las bboxes sobre las imágenes (frontales y traseras)
3. Haz clic sobre cada caja detectada o botón para sumar unidades (+1)
4. El proceso guarda tus respuestas y puede retomarse luego en `detections_labels.csv`

### 🧪 Testing
1. Selecciona las rutas al archivo del modelo Mask R-CNN y clasificador ConvNeXt.
2. Arranca el Pipeline Completo proporcionando una imagen frontal y otra trasera.
3. El frontend dibujará los bounding boxes y el conteo del ticket resultante del Árbol de Decisión.

### 📹 Extracción de Vídeo
1. Selecciona un vídeo `.mp4` de cámara de seguridad
2. Ajusta la ROI (zona de captura) sobre el primer frame
3. Elige tipo de cámara (delantera/trasera)
4. Configura umbral de confianza YOLO
5. Ejecuta → capturas automáticas cuando no hay personas visibles

**Lógica de captura:**
- Persona visible → se para
- Persona desaparece → espera 0.5s → captura
- Sin persona → captura cada 2s, máximo 5 seguidas
- Tras 5 capturas → para hasta ver otra persona

---

## Estructura

```
py_emparejado/
├── backend/                    # Flask API
│   ├── app.py                  # App factory
│   ├── config.py               # Configuración
│   ├── routes/                 # Endpoints API
│   └── services/               # Lógica de negocio
├── frontend/                   # React (Vite)
│   ├── dist/                   # Build pre-compilado (listo para usar)
│   ├── src/pages/              # Landing, Pairing, Cropping, VideoExtraction
│   └── src/components/         # Componentes reutilizables
├── run.py                      # Script de arranque
└── requirements.txt            # Dependencias Python
```

---

## Desarrollo del frontend

Solo si quieres modificar la UI:

```bash
# Instalar Node.js 18+ desde https://nodejs.org/
cd frontend
npm install
npm run dev     # Dev server en localhost:3000

# En otra terminal:
python run.py --dev   # Backend en localhost:5000
```

Para recompilar el frontend:
```bash
cd frontend && npm run build
```
