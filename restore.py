#!/usr/bin/env python3
"""Restore the locked skills next to this file; standard library, offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile


class RestoreError(Exception):
    pass


def relative_path(value, label):
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        raise RestoreError("Ruta inválida en {}: {!r}".format(label, value))
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in (".", "..") for part in path.parts):
        raise RestoreError("Ruta fuera del paquete en {}: {}".format(label, value))
    if path.as_posix() != value or not path.parts:
        raise RestoreError("Ruta no normalizada en {}: {}".format(label, value))
    if any(":" in part for part in path.parts):
        raise RestoreError("Ruta no portable en {}: {}".format(label, value))
    return path


def file_digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expected_files(records, label):
    if not isinstance(records, list) or not records:
        raise RestoreError("Falta el inventario de archivos de {}.".format(label))
    result = {}
    folded = set()
    for record in records:
        if not isinstance(record, dict):
            raise RestoreError("Entrada de archivo inválida en {}.".format(label))
        name = str(relative_path(record.get("path"), label))
        digest = record.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise RestoreError("SHA-256 inválido: {}/{}".format(label, name))
        if name.casefold() in folded:
            raise RestoreError("Ruta duplicada o ambigua: {}/{}".format(label, name))
        folded.add(name.casefold())
        result[name] = digest
    return result


def inventory(folder):
    """Hash ordinary files; reject symbolic links and non-file entries."""
    if folder.is_symlink() or not folder.is_dir():
        raise RestoreError("La carpeta no es un directorio normal: {}".format(folder))
    result = {}
    folded = set()
    for current, directories, files in os.walk(str(folder), followlinks=False):
        for name in directories + files:
            path = Path(current) / name
            if path.is_symlink():
                raise RestoreError("No se admiten enlaces simbólicos: {}".format(path))
            mode = path.stat().st_mode
            if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise RestoreError("Tipo de archivo no admitido: {}".format(path))
        for name in files:
            path = Path(current) / name
            relative = path.relative_to(folder).as_posix()
            relative_path(relative, str(folder))
            if relative.casefold() in folded:
                raise RestoreError("Ruta ambigua entre sistemas: {}".format(path))
            folded.add(relative.casefold())
            result[relative] = file_digest(path)
    return result


def check_file(root, name, digest):
    relative = relative_path(name, "sources.lock.json")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise RestoreError("No se admiten enlaces simbólicos: {}".format(current))
    if not current.is_file() or file_digest(current) != digest:
        raise RestoreError("Falta un archivo o su hash no coincide: {}".format(name))


def load_package(root):
    lock_path = root / "sources.lock.json"
    if lock_path.is_symlink():
        raise RestoreError("sources.lock.json no puede ser un enlace simbólico.")
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RestoreError("No se puede leer sources.lock.json: {}".format(error))
    if not isinstance(lock, dict) or lock.get("schema_version") != 1:
        raise RestoreError("Versión de sources.lock.json no compatible; se requiere 1.")
    if lock.get("hash_algorithm") != "sha256":
        raise RestoreError("El inventario debe usar hash_algorithm: sha256.")
    records = lock.get("skills")
    if records is None:
        records = []
        for source in lock.get("sources", []):
            records.extend(source.get("skills", []))
    if not isinstance(records, list) or not records:
        raise RestoreError("El inventario no contiene skills.")
    skills = []
    names = set()
    combined = {}
    for record in records:
        if not isinstance(record, dict):
            raise RestoreError("Entrada de skill inválida.")
        name = record.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
            raise RestoreError("Nombre de skill no portable: {!r}".format(name))
        if name in names:
            raise RestoreError("Skill duplicada: {}".format(name))
        names.add(name)
        path = str(relative_path(record.get("path"), name))
        if path != "skills/" + name:
            raise RestoreError("Ruta de skill inesperada: {}".format(path))
        files = expected_files(record.get("files"), name)
        if "SKILL.md" not in files:
            raise RestoreError("Falta SKILL.md en {}.".format(name))
        folder = root.joinpath(*PurePosixPath(path).parts)
        if inventory(folder) != files:
            raise RestoreError("El inventario o los hashes no coinciden: {}".format(path))
        text = (folder / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)
        if len(frontmatter) != 3 or frontmatter[0].strip():
            raise RestoreError("Frontmatter inválido en {}/SKILL.md.".format(path))
        match = re.search(r"^name:\s*['\"]?([a-z0-9][a-z0-9-]*)['\"]?\s*$", frontmatter[1], re.M)
        if not match or match.group(1) != name:
            raise RestoreError("El nombre interno no coincide: {}".format(name))
        for file_name, digest in files.items():
            combined[path + "/" + file_name] = digest
        skills.append({"name": name, "source": folder, "files": files})
    if "files" in lock and expected_files(lock["files"], "files") != combined:
        raise RestoreError("El inventario global difiere del inventario de las skills.")
    if "third_party_files" in lock:
        for name, digest in expected_files(lock["third_party_files"], "third_party_files").items():
            check_file(root, name, digest)
    return skills


def preflight(skills, destination):
    if destination.exists() and not destination.is_dir():
        raise RestoreError("El destino no es una carpeta: {}".format(destination))
    pending = []
    skipped = []
    conflicts = []
    for skill in skills:
        target = destination / skill["name"]
        if target.is_symlink():
            conflicts.append(skill["name"] + " (enlace simbólico)")
        elif target.exists():
            try:
                identical = inventory(target) == skill["files"]
            except RestoreError:
                identical = False
            if identical:
                skipped.append(skill)
            else:
                conflicts.append(skill["name"])
        else:
            pending.append(skill)
    if conflicts:
        raise RestoreError(
            "Hay skills existentes distintas: {}. No se cambió ninguna skill. "
            "Elige otra carpeta con --dest o revisa esas copias por separado.".format(
                ", ".join(conflicts)
            )
        )
    return pending, skipped


def restore(skills, destination, check_only):
    pending, skipped = preflight(skills, destination)
    print("Destino: {}".format(destination))
    print("Paquete validado: {} skills, {} archivos.".format(
        len(skills), sum(len(skill["files"]) for skill in skills)))
    if check_only:
        print("Comprobación sin cambios: {} para instalar; {} idénticas.".format(
            len(pending), len(skipped)))
        return
    if not pending:
        print("Sin cambios: {} skills idénticas ya instaladas.".format(len(skipped)))
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        with tempfile.TemporaryDirectory(prefix=".web-creative-restore-", dir=str(destination.parent)) as temp:
            staging = Path(temp)
            for skill in pending:
                staged = staging / skill["name"]
                shutil.copytree(str(skill["source"]), str(staged))
                if inventory(staged) != skill["files"]:
                    raise RestoreError("La copia temporal no coincide: {}".format(skill["name"]))
            # Recheck every target after staging, before creating any skill.
            current_pending, _ = preflight(skills, destination)
            if {s["name"] for s in current_pending} != {s["name"] for s in pending}:
                raise RestoreError("El destino cambió durante la comprobación. Vuelve a ejecutar.")
            destination.mkdir(parents=True, exist_ok=True)
            for skill in pending:
                target = destination / skill["name"]
                target.mkdir()  # Exclusive: never replace an existing skill.
                created.append(target)
                shutil.copytree(str(staging / skill["name"]), str(target), dirs_exist_ok=True)
                if inventory(target) != skill["files"]:
                    raise RestoreError("La copia instalada no coincide: {}".format(skill["name"]))
    except (OSError, RestoreError):
        # Only directories newly reserved by this invocation are rolled back.
        for target in reversed(created):
            shutil.rmtree(str(target))
        raise
    print("Instaladas: {}. Ya idénticas: {}. Total: {}.".format(
        len(pending), len(skipped), len(skills)))
    print("Abre un nuevo chat o turno de Codex para que detecte las skills.")


def main():
    parser = argparse.ArgumentParser(
        description="Restaura las skills verificadas de este repositorio, sin red ni sobrescrituras.")
    parser.add_argument("--dest", type=Path, default=Path.home() / ".agents" / "skills",
                        help="Carpeta de skills (por defecto: ~/.agents/skills).")
    parser.add_argument("--check", action="store_true",
                        help="Valida el paquete y los conflictos sin instalar.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    destination = args.dest.expanduser().resolve()
    try:
        skills = load_package(root)
        if destination == root or root in destination.parents:
            raise RestoreError("El destino debe estar fuera de este repositorio.")
        restore(skills, destination, args.check)
    except (RestoreError, OSError, ValueError, KeyError, TypeError) as error:
        print("Error: {}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
