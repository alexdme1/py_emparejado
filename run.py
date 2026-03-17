#!/usr/bin/env python3
"""
run.py — Script único de arranque de la aplicación.

Uso:
    python run.py              # Arranque normal
    python run.py --dev        # Modo desarrollo (solo backend, sin build)
    python run.py --build      # Forzar rebuild del frontend
"""

import os
import sys
import subprocess
import webbrowser
import argparse
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')
FRONTEND_DIST = os.path.join(FRONTEND_DIR, 'dist')


def check_node():
    """Verifica que Node.js y npm están disponibles."""
    try:
        subprocess.run(
            ['node', '--version'],
            capture_output=True, check=True,
            shell=(sys.platform == 'win32'),
        )
        subprocess.run(
            ['npm', '--version'],
            capture_output=True, check=True,
            shell=(sys.platform == 'win32'),
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_frontend_deps():
    """Instala dependencias del frontend si no existen."""
    node_modules = os.path.join(FRONTEND_DIR, 'node_modules')
    if not os.path.isdir(node_modules):
        print("Instalando dependencias del frontend...")
        subprocess.run(
            ['npm', 'install'], cwd=FRONTEND_DIR, check=True,
            shell=(sys.platform == 'win32'),
        )
    else:
        print("[OK] Dependencias del frontend ya instaladas.")


def build_frontend():
    """Compila el frontend React."""
    print("Compilando frontend React...")
    subprocess.run(
        ['npm', 'run', 'build'], cwd=FRONTEND_DIR, check=True,
        shell=(sys.platform == 'win32'),
    )
    print("[OK] Frontend compilado en frontend/dist/")


def main():
    parser = argparse.ArgumentParser(description='Arrancar la aplicacion')
    parser.add_argument('--dev', action='store_true',
                        help='Modo desarrollo (solo backend)')
    parser.add_argument('--build', action='store_true',
                        help='Forzar rebuild del frontend')
    parser.add_argument('--port', type=int, default=5000,
                        help='Puerto del servidor (default: 5000)')
    parser.add_argument('--no-browser', action='store_true',
                        help='No abrir el navegador automaticamente')
    args = parser.parse_args()

    # ── Frontend: solo compilar si se pide o si no existe dist/ ──
    if args.build:
        if not check_node():
            print("[ERROR] Node.js/npm no encontrado. Instalalo desde https://nodejs.org/")
            sys.exit(1)
        if os.path.isdir(FRONTEND_DIR):
            install_frontend_deps()
            build_frontend()
    elif not args.dev and not os.path.isdir(FRONTEND_DIST):
        # dist/ no existe y no es modo dev → intentar compilar
        if check_node() and os.path.isdir(FRONTEND_DIR):
            install_frontend_deps()
            build_frontend()
        else:
            print("[AVISO] frontend/dist/ no encontrada y Node.js no disponible.")
            print("        El frontend no se mostrara. Instala Node.js y ejecuta:")
            print("        cd frontend && npm install && npm run build")
    else:
        if os.path.isdir(FRONTEND_DIST):
            print("[OK] Frontend pre-compilado encontrado.")

    # ── Arrancar Flask ──
    print(f"\n>>> Arrancando servidor en http://localhost:{args.port}")
    print(f"    Presiona Ctrl+C para detener.\n")

    sys.path.insert(0, PROJECT_ROOT)
    from backend.app import create_app

    app = create_app()

    if not args.no_browser:
        def open_browser():
            time.sleep(1.5)
            webbrowser.open(f'http://localhost:{args.port}')

        import threading
        threading.Thread(target=open_browser, daemon=True).start()

    app.run(debug=args.dev, port=args.port, host='0.0.0.0')


if __name__ == '__main__':
    main()
