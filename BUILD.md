# Build y distribución

Guía para compilar localmente Retro Audit Commander y preparar artefactos distribuibles.

## Requisitos

- Sistema operativo nativo de destino: Linux, macOS o Windows.
- `uv` instalado y disponible en `PATH`.
- Acceso a Internet para que `uv` pueda descargar Python y dependencias la primera vez.
- Espacio suficiente para el entorno virtual y los temporales de PyInstaller.

No es necesario instalar Python globalmente: `uv` selecciona o descarga la versión indicada en `.python-version` y utiliza las versiones bloqueadas en `uv.lock`.

## Compilación local

Ejecuta el wrapper correspondiente desde la raíz del repositorio:

### Linux o WSL

```text
scripts/build-local-linux.sh --clean
```

WSL produce un ejecutable Linux; no genera un ejecutable Windows.

### macOS

```text
scripts/build-local-macos.sh --clean
```

La arquitectura del artefacto corresponde a la arquitectura del runner macOS utilizado.

### Windows PowerShell

```text
scripts\\build-local-windows.ps1 -Clean
```

Si la política de PowerShell bloquea scripts locales, aplica la política adecuada para tu usuario o ejecuta el script desde una sesión autorizada por tu entorno corporativo.

## Opciones

Los wrappers delegan en `scripts/build_local.py`:

| Linux/macOS | Windows | Función |
|---|---|---|
| `--clean` | `-Clean` | Elimina el build local anterior. |
| `--skip-tests` | `-SkipTests` | Omite `pytest`; usar solo de forma consciente. |
| `--output PATH` | `-Output PATH` | Cambia el directorio de salida. |
| `--verbose` | `-VerboseBuild` | Activa el modo detallado del build. |

Las pruebas se ejecutan por defecto.

## Etapas ejecutadas

El orquestador realiza, en este orden:

1. Sincroniza dependencias con `uv sync --locked --group dev`.
2. Ejecuta la suite de pruebas, salvo que se use `--skip-tests`.
3. Genera el wheel del proyecto.
4. Construye el ejecutable PyInstaller en formato `onedir`.
5. Ejecuta el smoke test `retro-audit --version`.
6. Genera un SBOM CycloneDX reproducible.
7. Crea un archivo `.tar.gz` en Unix o `.zip` en Windows.
8. Genera sidecars SHA-256 para el archivo y el SBOM.

La configuración de PyInstaller está centralizada en `packaging/retro_audit.spec`.

## Artefactos

Por defecto se generan en `release/`:

- `retro-audit-<os>-<arquitectura>.tar.gz` o `.zip`: distribución ejecutable.
- `retro-audit-<os>-<arquitectura>.cdx.json`: SBOM CycloneDX.
- Archivos `.sha256`: hashes verificables de cada artefacto.

Los temporales se guardan en `build/local/`, directorio ignorado por Git.

Para probar el ejecutable desempaquetado:

```text
build/local/linux-x64/dist/retro-audit/retro-audit --version
```

El nombre y la extensión cambian en Windows y macOS. El smoke test puede ejecutarse manualmente con:

```text
uv run python scripts/smoke_test_artifact.py build/local/linux-x64/dist/retro-audit
```

## Compatibilidad y seguridad

Cada plataforma debe compilarse en su propio sistema operativo. Un binario Linux no es intercambiable con Windows o macOS.

Antes de publicar una release:

- Ejecuta las pruebas y el smoke test sin `--skip-tests`.
- Verifica los SHA-256 después de transferir los archivos.
- Incluye `LICENSE` y el aviso de uso autorizado.
- Revisa el SBOM y las licencias de dependencias.
- Firma los artefactos con Authenticode en Windows o Developer ID/notarización en macOS cuando corresponda.
- No incluyas informes, claves, certificados ni archivos `.env` en el paquete.

La firma no forma parte del build local por defecto y debe ejecutarse en una fase separada con credenciales protegidas.

## Releases oficiales

El workflow `.github/workflows/release.yml` reproduce este flujo en runners nativos de GitHub Actions para Windows, Linux y macOS. Los scripts locales sirven para desarrollo, diagnóstico y validación; las releases oficiales deben generarse desde un tag mediante CI.
