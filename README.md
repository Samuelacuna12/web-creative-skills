# Web Creative Skills

Respaldo privado y portable de **37 skills**, con **89 archivos** de instrucciones y referencias. Reúne GSAP oficial (8), Interfaces (8), animación de Emil Kowalski (9), React Three Fiber (11) y Spline oficial (1).

Las versiones de origen quedan fijadas por commit en [sources.lock.json](sources.lock.json). Las carpetas de [skills/](skills/) conservan sus archivos originales y sus referencias. Los créditos y las evidencias de licencia se incluyen en [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt) y `third-party/`.

## Restaurar en otro Mac

Necesitas Python 3.9 o posterior y acceso al repositorio privado [Samuelacuna12/web-creative-skills](https://github.com/Samuelacuna12/web-creative-skills). Tu acceso a GitHub debe estar configurado para clonarlo:

```bash
git clone https://github.com/Samuelacuna12/web-creative-skills.git
cd web-creative-skills
python3 restore.py --check
python3 restore.py
```

La carpeta predeterminada es `~/.agents/skills`. El instalador comprueba todos los hashes SHA-256 antes de copiar, conserva las subcarpetas y no descarga nada ni ejecuta código de las skills. Después de clonar, la restauración funciona sin conexión.

En la instalación de Codex del Mac donde se preparó este respaldo, las skills se cargaron desde `~/.codex/skills`. Para restaurar en esa misma ubicación, o para una versión de Codex que la utilice, indica el destino expresamente:

```bash
python3 restore.py --dest "$HOME/.codex/skills" --check
python3 restore.py --dest "$HOME/.codex/skills"
```

Usa una sola ubicación para evitar duplicados. También puedes elegir cualquier otra carpeta con `--dest`. El script localiza el respaldo a partir de su propia ubicación, así que puede ejecutarse desde otra carpeta. Abre un nuevo chat o turno de Codex tras la restauración.

## Si ya tienes alguna skill

- Si todos sus archivos coinciden con el respaldo, se omite y queda intacta.
- Si existe una versión distinta, la operación se detiene **antes de instalar ninguna skill**. Revisa esa carpeta o elige otro destino; el script no la sobrescribe.
- Ejecutar de nuevo el instalador sobre una restauración completa no modifica archivos.

`--check` valida el paquete y comprueba los conflictos sin instalar. Si falla un hash del respaldo, recupera una copia íntegra del repositorio antes de continuar.

## Qué queda instalado

Las skills son instrucciones para el agente. Ayudan a decidir y construir interfaces, movimiento, escenas 3D y sus detalles de implementación. Este respaldo no instala las bibliotecas que necesita una web: GSAP, React, Three.js, React Three Fiber y otras dependencias se eligen e instalan en cada proyecto cuando corresponda.

Tampoco contiene cuentas, sesiones, claves, permisos ni conexiones. Por ejemplo, la skill de Spline necesita una conexión activa a Spline para manejar su editor. Los servicios o herramientas que use una skill se configuran aparte.

Refero y los demás plugins ya disponibles se gestionan desde sus propias instalaciones; no forman parte de estas 37 skills. El respaldo no añade instrucciones globales ni cambia los proyectos existentes.

## Copia local y actualizaciones

Clonar el repositorio crea una copia local. **No activa sincronización automática** entre Macs ni actualiza por sí solo las skills instaladas. Una actualización del repositorio requiere descargarla y revisar sus cambios; después, el instalador volverá a detenerse si encuentra versiones instaladas diferentes.

Para trasladarlo sin Git, copia la carpeta completa a otro Mac, incluyendo `restore.py`, `sources.lock.json`, `skills/`, los avisos y las evidencias de licencia. Ejecuta allí los mismos comandos de Python. Conserva este repositorio como privado y respeta los avisos de cada autor.
