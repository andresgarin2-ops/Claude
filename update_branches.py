import subprocess
import sys


BRANCHES = ["main", "scraper", "claude/demo-capabilities-T6xv9"]


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def current_branch():
    _, out, _ = run(["git", "branch", "--show-current"])
    return out


def update_branch(branch):
    print(f"\n--- Actualizando '{branch}' ---")

    # Verificar si la rama existe localmente
    code, _, _ = run(["git", "show-ref", "--verify", f"refs/heads/{branch}"])
    exists_locally = code == 0

    if exists_locally:
        run(["git", "checkout", branch])
        code, out, err = run(["git", "pull", "origin", branch])
    else:
        # Intentar crear la rama desde el remoto
        code, out, err = run(["git", "fetch", "origin", f"{branch}:{branch}"])

    if code == 0:
        print(f"OK: {out or 'Actualizado correctamente'}")
    else:
        print(f"ERROR: {err or 'No se pudo actualizar'}")

    return code == 0


def main():
    original = current_branch()
    print(f"Rama actual: {original}")

    results = {}
    for branch in BRANCHES:
        results[branch] = update_branch(branch)

    # Volver a la rama original
    run(["git", "checkout", original])
    print(f"\nVuelto a: {original}")

    # Resumen
    print("\n=== Resumen ===")
    for branch, ok in results.items():
        status = "OK" if ok else "FALLO"
        print(f"  {status}  {branch}")

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
