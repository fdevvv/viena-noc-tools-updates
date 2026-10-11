# VIENA NOC Tools · Transición desde .42

**Actualización manual 1.3.43 · Transición a Chrome Web Store**

Este paquete prepara tu instalación manual .42 para trasladar su configuración. Conserva las funciones de la .42 y agrega el puente. Las nuevas funciones se reciben al instalar la versión de Chrome Web Store.

## Paso 1: actualizar la instalación manual

1. Identificá la carpeta desde la que Chrome carga tu extensión manual .42 y conservá una copia de esa carpeta.
2. Cerrá las páginas corporativas. Extraé `VIENA_NOC_Tools_TRANSICION_DESDE_42_1.3.43.zip` y copiá sus archivos **sobre la misma carpeta original**, reemplazando los correspondientes y conservando el resto.
3. En `chrome://extensions`, recargá esa instalación. No la desinstales ni la cargues desde otra carpeta: conservar la instalación permite mantener su ID y configuración.

Este procedimiento directo requiere recargar manualmente. El paquete también tiene formato portable para el updater, pero aún no se publicó como actualización remota.

## Paso 2: instalar desde Chrome Web Store

1. Conservá la instalación manual actualizada, instalada y activa.
2. En el mismo perfil de Chrome, instalá [VIENA NOC Tools desde la tienda](https://chromewebstore.google.com/detail/kncbbeclddielngolalkmlclfljgaoje). Mientras la distribución sea para testers, tu cuenta Google debe estar habilitada como tester.
3. Pulsá **Buscar mi instalación anterior** y aceptá el permiso. Si hay varias instalaciones, elegí la manual correcta y confirmá el traslado.
4. Verificá macros, templates, botones, usuario y preferencias de zoom/vista. El origen se desactiva después de la copia verificada y conserva sus datos para recuperación.

**1.3.43 manual = transición. 1.3.43 de tienda = nuevas funciones y actualizaciones por Chrome.**

## Estado de entrega

Copia identificada del paquete de transición candidate1 existente, sin cambiar sus bytes ni la versión publicada en tienda. SHA256 del ZIP: `306a002b55de0c2640719bd8cbefb467ddb4564c06e86974ec2d2d14c5594de6`.

Preflight portable PASS. Las pruebas anteriores del puente están en `artifacts/manual-release-1.3.43-bridge/candidate1/`; la prueba de carpeta/permisos Windows del operador y su revisión siguen pendientes. Este nombre de descarga e instrucciones no cambian el nombre visible dentro del panel ni publican la actualización remota.
