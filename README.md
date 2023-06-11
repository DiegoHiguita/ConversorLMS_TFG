# ConversorLMS_TFG
Conversor LMS, entre formatos MoodleXML - QTI/IMS

En este repositorio puede encontrar tres ejecutables, cada uno en una carpeta:
  - EjecutableLinux -> Dentro de esta carpeta encontramos un eejcutable para  el sistema operativo Linux, solo tendrás que clickar en "gui"
  - EjecutableWindows -> Dentro de esta carpeta encontramos un eejcutable para  el sistema operativo Windows, solo tendrás que clickar en "gui.exe"
  - EjecutableMac -> Dentro de esta carpeta encontramos un eejcutable para  el sistema operativo Mac, solo tendrás que clickar en "gui.app"

Antes de ejecutar el programa, asegurese de que tiene los permisos de ejecución activados.

  -En Linux puede seguir estos pasos:
    -1. Click derecho sobre el ejecutable(el programa)
    -2. Buscar 'Propiedades'
    -3. En la pestaña de 'Permisos' podrá permitir que el archivo se ejecute como un programa

  -En Windows puede seguir estos pasos: 
    -1. Haciendo clic derecho sobre la carpeta o archivo en cuestión
    -2. Seleccionando 'Propiedades'
    -3. podemos ver los permisos en la pestaña 'Seguridad'. Los tipos de acceso
    que se pueden establecer son control total (todos los permisos disponibles), modificar, lectura y ejecución, lectura, escritura y los permisos especiales.
  
  -En Mac puede seguir estos pasos:
    -1. Haz clic derecho (o Control + clic) en el programa 
    -2. Selecciona "Obtener información" en el menú contextual.Se abre una ventana de informacion para el programa. 
    -3. En la sección "General", asegúrese de que la opción "Bloqueado" esté desmarcada. Si está marcada, haz clic en el candado en la 
    esquina inferior derecha de la ventana y proporciona tus credenciales de administrador para desbloquear los cambios.
    -4. En la sección "Permisos", haz clic en el triángulo al lado de "Todos" para expandir las opciones.
    -5. Junto a "Derechos de acceso", seleccione "Leer y escribir" para otorgar permisos de ejecución.

  
-------------------------------------------------------------------------------------------------------------------------------------------
Si durante el lanzamiento del ejecutable ha surgido algún tipo de error, en este caso,
podremos ejecutar el código fuente, para ello deberemos tener instalado en su dispositivo:
  - python (https://www.python.org)
  - La biblioteca lxml de python (pip install lxml)
