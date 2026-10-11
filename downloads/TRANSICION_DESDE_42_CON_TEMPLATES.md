# 1.3.43 · Transición desde .42 con respaldo de templates

Actualización para la extensión manual .42. Conserva sus funciones y prepara el traslado a Chrome Web Store. Incluye Personalización → Respaldo de templates para exportar/importar juntas las bibliotecas guardadas de VIENA, edificio y cuadras, con opciones y templates de botones personales.

## Actualizar la instalación manual

Cuando se active en el updater, buscá la actualización desde el panel de tu .42 y aplicala usando su carpeta vinculada. Conservá esa instalación y sus datos. No la desinstales para actualizar.

Para prueba manual de esta candidata: conservá una copia de la carpeta original, cerrá las páginas corporativas, extraé VIENA_NOC_Tools_TRANSICION_DESDE_42_1.3.43_CON_RESPALDO_TEMPLATES.zip y copiá sus archivos sobre la misma carpeta de .42, reemplazando los correspondientes. Conservá el resto de la carpeta y recargá esa instalación en chrome://extensions. No cargues otra carpeta como extensión nueva.

## Trasladar toda la configuración

Instalá [VIENA NOC Tools de Chrome Web Store](https://chromewebstore.google.com/detail/kncbbeclddielngolalkmlclfljgaoje) en el mismo perfil de Chrome, dejando la manual activa. La cuenta Google debe estar habilitada mientras la ficha sea para testers. Pulsá Buscar mi instalación anterior, aceptá el permiso y confirmá el origen. Verificá macros, templates, botones, usuario y preferencias. El origen se desactiva después del traslado verificado y conserva los datos.

## Respaldo manual de templates

En la manual actualizada, abrí Personalización → Respaldo de templates → Exportar templates. El JSON contiene sólo templates/configuraciones; no incluye ni cambia usuario, identidad, macros o zoom. Los defaults no guardados ya están incluidos en la extensión.

Para restaurar en esta actualización: seleccioná el archivo en Respaldo de templates, revisá las cantidades y confirmá Importar templates. Se reemplazan sólo las bibliotecas incluidas; exportá antes el respaldo actual para recuperación.

Para restaurar en la versión de tienda actual: abrí Respaldo de instalación, seleccioná ese JSON y confirmá Restaurar configuración. Como el archivo sólo contiene templates, las demás preferencias se conservan. Los templates vinculados a un operador conservan su usuario de origen; configurá el mismo usuario VIENA para usarlos.

## Estado de esta candidata

Preparada para revisión, sin activación remota del updater al redactar esta guía. La versión de tienda no se modifica. No incluye el nuevo anuncio de novedades ni el aviso guiado hacia tienda. SHA256 del ZIP: 961abfc8e31776221f91f0e46e532d59176b0269a13573feeb68bbea97259c51.
