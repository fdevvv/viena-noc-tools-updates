# VIENA NOC Tools — actualización manual de transición

[Descargar el ZIP de transición 1.3.43](https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/downloads/VIENA_NOC_Tools_TRANSICION_1.3.43.zip)

Esta actualización mantiene las funciones de la instalación manual e incorpora el traslado a la extensión de Chrome y los respaldos completos e individuales.

## Actualizar la instalación manual

1. Conservá la extensión instalada y su carpeta actual. No la desinstales ni cargues una carpeta diferente.
2. Extraé el ZIP y reemplazá los archivos dentro de esa misma carpeta. El manifest.json debe quedar directamente dentro de la carpeta que Chrome ya utiliza.
3. En chrome://extensions, pulsá Recargar en esa extensión. Comprobá que muestra 1.3.43 · Transición y que conserva tus macros, templates y preferencias.
4. Si querés una copia adicional, abrí Personalización → Respaldo completo → Exportar configuración completa. Guardá el archivo en un lugar privado.

Si ya recibiste la actualización con el updater, no necesitás reemplazar los archivos manualmente.

## Pasar a Chrome Web Store

1. Usá el mismo perfil de Chrome. La cuenta de Google debe tener acceso a la ficha si todavía está disponible sólo para testers.
2. Instalá [VIENA NOC Tools desde Chrome Web Store](https://chromewebstore.google.com/detail/kncbbeclddielngolalkmlclfljgaoje), conservando activa la instalación manual de transición.
3. Cerrá las páginas operativas mientras trasladás los datos. En Traer tu configuración anterior, pulsá Buscar mi instalación anterior, concedé el permiso solicitado y elegí la instalación manual correcta si aparece más de una.
4. Confirmá el traslado y verificá macros, templates, usuario, zoom y vistas en la extensión de tienda. El traslado verificado desactiva la instalación de origen y conserva sus datos para recuperación.

No borres la instalación de origen ni su carpeta hasta verificar que todo está correcto en la extensión de tienda.

## Respaldos

Respaldo completo exporta toda la configuración en un archivo. Al importar en esta versión de transición, agrega lo que falta, omite coincidencias exactas y conserva los valores actuales cuando hay diferencias. Respaldos individuales abre templates, macros o botones en páginas separadas.

La página de restauración de instalación de la versión de tienda ya publicada conserva su comportamiento anterior de reemplazo. Para el traslado a tienda, usá el flujo Traer tu configuración anterior indicado arriba.
