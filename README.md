# Retro Audit Commander

TUI con estética MS-DOS para comprobaciones **autorizadas** y de bajo impacto:

- Comprobación TCP de una lista fija de puertos comunes, con timeout corto.
- Auditoría de cabeceras HTTP y atributos de seguridad de cookies, sin registrar sus valores.
- Verificación TLS: protocolo negociado, cifrado y validación del certificado.
- Banner Grabbing de servicios comunes mediante sockets de bajo nivel, con lectura acotada y salida sanitizada.
- Verificación de una única credencial SSH autorizada, sin reintentos y con validación estricta de clave de host.
- Auditoría offline de fortaleza de contraseñas y simulación local de políticas de bloqueo.
- Auditoría defensiva de negociación/configuración SSH, sin probar contraseñas.
- Detección local de intentos repetidos de autenticación SSH en logs acotados.
- Exportación de los resultados a `reports/` en formato TXT.

La aplicación exige confirmar que se tiene autorización antes de ejecutar cualquier comprobación. Úsala únicamente en sistemas propios o dentro de un alcance autorizado.

## Interfaz Commander

La UI se inspira en los gestores de archivos DOS, con dos paneles, barra de menús y ventanas flotantes. Los menús **Archivo**, **Auditoría**, **Ventana** y **Ayuda** se abren con ratón o teclado y las auditorías conservan estos atajos:

- `F1`: comprobación TCP.
- `F2`: auditoría HTTP.
- `F3`: auditoría TLS.
- `F4`: Banner Grabbing.
- `F5`: verificación única de credencial SSH.
- `F6`: fortaleza de contraseña offline.
- `F7`: simulador local de bloqueo.
- `F8`: configuración SSH.
- `F10`: detección defensiva en logs.
- `R`: guardar el informe actual.

Durante una auditoría, el panel de comandos muestra una animación ASCII de radar sincronizada con el estado y el visor registra cada etapa en tiempo real. El catálogo de comandos se restaura automáticamente al terminar.

### Splash Screen

Al iniciar, Retro Audit muestra durante 2,5 segundos una animación CRT con radar, progreso y versión. Cualquier tecla o clic permite continuar inmediatamente. La opción **Ayuda → Repetir inicio** vuelve a mostrarla.

Para automatización o accesibilidad pueden definirse estas variables opcionales:

- `RETRO_AUDIT_SKIP_SPLASH=1`: omite la pantalla inicial.
- `RETRO_AUDIT_REDUCED_MOTION=1`: sustituye la animación por una pantalla estática breve.

### Ayuda integrada

El menú **Ayuda** permite abrir la guía desplazable, repetir la pantalla de inicio o consultar **Acerca de**. Esta última ventana presenta la versión, finalidad defensiva, autoría, licencia, advertencia de uso autorizado, versiones del entorno y enlaces oficiales del proyecto.

Cada ficha de la guía explica:

- Qué hace la herramienta.
- Cómo preparar el objetivo y utilizarla paso a paso.
- Qué información contiene el resultado.
- Qué límites de seguridad aplica.

Las herramientas que requieren parámetros también muestran sus instrucciones directamente en el formulario antes de ejecutar la comprobación.

## Arquitectura

La aplicación está dividida por responsabilidades y `main.py` actúa únicamente como punto de entrada:

```text
retro_audit/
├── contracts.py          # Resultado y callback de progreso compartidos
├── factory.py            # Creación e inyección de servicios
├── metadata.py           # Identidad y versiones de proyecto/runtime
├── registry.py           # Registro extensible de herramientas
├── reporting.py          # Persistencia de informes
├── targets.py            # Normalización y validación de objetivos
├── tools/
│   ├── network.py        # Auditoría TCP
│   ├── http_headers.py   # Cabeceras y cookies
│   ├── tls.py            # Certificados y negociación TLS
│   ├── banner.py         # Identificación acotada de servicios
│   ├── ssh_credential.py # Una credencial, un intento, host key estricta
│   ├── ssh_configuration.py # Negociación y métodos SSH
│   ├── password_strength.py # Evaluación exclusivamente local
│   ├── lockout_simulator.py # Simulación en memoria
│   └── brute_force_logs.py  # Detección defensiva en logs locales
└── ui/
	├── about.py          # Ventana Acerca de desplazable
	├── app.py            # Orquestación Textual
	├── constants.py      # CSS, menús y animaciones
	├── splash.py         # Splash, configuración y fábrica de pantallas
	└── screens.py        # Ventanas modales
tests/                    # Regresiones de arquitectura, UI y seguridad
```

Las herramientas no importan Textual ni `main.py`. La UI recibe un agregado `ApplicationServices` creado por `AuditServiceFactory`, lo que permite sustituir implementaciones en pruebas sin modificar la presentación. Las herramientas implementan un protocolo común, incorporan su propia ficha `ToolGuide` y se descubren mediante `ToolRegistry`.

Consulta `ARCHITECTURE.md` para las reglas de dependencia y `SECURITY.md` para el modelo de amenazas, controles y limitaciones conocidas.

## Proyecto

- Repositorio: <https://github.com/mapenzo/retro-audit-commander>
- Autor: Miguel Poveda ([mapenzo](https://github.com/mapenzo))
- Licencia: [MIT](LICENSE)

## Instalación y uso

Instala las dependencias del proyecto con tu gestor de entornos Python preferido y ejecuta `main.py`. La interfaz incluye atajos: `r` guarda el informe actual y `Ctrl+C` sale.

## Distribución ejecutable

Las versiones publicadas incluyen ejecutables nativos por plataforma, por lo que no requieren una instalación previa de Python. El flujo de distribución crea inicialmente una carpeta ejecutable (`onedir`) llamada `retro-audit`; se conserva así para facilitar diagnóstico y soporte. Los artefactos contienen el ejecutable, sus dependencias y la metadata necesaria para mostrar la versión correctamente.

Cada binario se compila en su plataforma de destino: Windows, Linux y macOS requieren artefactos independientes. Un binario generado desde Linux o WSL no es compatible con Windows ni macOS.

Para quienes mantienen el proyecto, `pyproject.toml` declara el grupo `dev` y `packaging/retro_audit.spec` concentra la configuración de PyInstaller. La automatización de release ejecuta pruebas, genera el paquete, comprueba `retro-audit --version` y publica hashes SHA-256 junto a un SBOM CycloneDX. El proceso completo de compilación local, sus opciones y los criterios de distribución están documentados en [BUILD.md](BUILD.md).

Los informes siguen guardándose en `reports/` relativo al directorio desde el que se inicia el ejecutable; úsalo desde una ubicación escribible. Cada plataforma debe compilarse nativamente: Linux/WSL produce Linux, no Windows ni macOS.

Antes de distribuir públicamente un artefacto, se debe adjuntar la licencia, conservar el aviso de uso autorizado, publicar su hash y firmarlo con el mecanismo de la plataforma (Authenticode en Windows y Developer ID/notarización en macOS). También se recomienda adjuntar un SBOM de las dependencias bloqueadas.

## Alcance

No realiza explotación, fuerza bruta, suplantación ARP, captura de tráfico, enumeración de rutas ni envío de payloads. La verificación SSH acepta una sola credencial introducida por el operador y hace exactamente una llamada de conexión, sin agentes, búsqueda de claves ni reintentos. Las contraseñas no aparecen en eventos ni resultados. El escaneo está limitado a puertos comunes definidos en el código y usa conexiones TCP con timeout breve. Las comprobaciones web son pasivas y respetan las respuestas `HTTP 429` sin reintentos automáticos.
