"""Положить заверенную маковскую раздачу в черновик выпуска.

    python install/release-mac.py v0.2.1

Зовёт её автор, на своём Mac, после того как `release.yml` сделал
черновик выпуска по метке. Сборочная машина GitHub маковский архив
по-прежнему собирает — как проверку, что код под меткой собирается, —
но в черновик его НЕ кладёт: подписать именем автора она не может,
сертификат лежит только у него (решение 31-й сессии; почему не отдать
сертификат GitHub — `docs/decisions.md`, «Заверение у Apple»).

## Что делает, по шагам

1. убеждается, что выпуск — ЧЕРНОВИК: опубликованный не трогается
   никогда, как и в `release.yml`;
2. достаёт код ровно под меткой во времянку (`git worktree`), а не
   берёт рабочую папку: туда могло попасть незакоммиченное, и архив
   разошёлся бы с меткой молча — ровно то, ради чего мак когда-то
   собирали на GitHub;
3. собирает раздачу оттуда с `--notarize` — подпись автора, заверение
   у Apple, проверка распаковкой (`build-release.py`);
4. кладёт архив в черновик и дописывает его сумму в `SHA256SUMS.txt`,
   не трогая виндовую строку.

**Без этого шага в черновике нет маковского архива вовсе** — и это
нарочно: пустое место видно, а архив без заверения выглядит ровно
как заверенный.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ЗДЕСЬ = Path(__file__).resolve().parent
КОРЕНЬ = ЗДЕСЬ.parent
АРХИВ = "Vertcut-mac.zip"
СУММЫ = "SHA256SUMS.txt"


def выполнить(команда: list[str], **к) -> subprocess.CompletedProcess:
    return subprocess.run(команда, check=True, text=True, **к)


def имя_репозитория(адрес: str) -> str:
    """`владелец/имя` из адреса `origin` — для `gh --repo`.

    Без `--repo` `gh` сам выбирает репозиторий, а у рабочей копии автора
    их два (`origin` — открытый, `dev` — старый закрытый): на выпуске
    0.2.1 `gh` отказал «No default remote repository». Черновик лежит
    там, куда уходит метка, — то есть в `origin`.
    """
    найдено = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$", адрес)
    if not найдено:
        raise SystemExit(f"The origin remote isn't a GitHub address: {адрес}")
    return найдено.group(1)


def репозиторий() -> str:
    адрес = выполнить(["git", "remote", "get-url", "origin"], cwd=КОРЕНЬ,
                      capture_output=True).stdout.strip()
    return имя_репозитория(адрес)


def черновик_ли(метка: str, репо: str) -> None:
    """Отказ словами, если выпуска нет или он уже опубликован."""
    вышло = subprocess.run(
        ["gh", "release", "view", метка, "--repo", репо,
         "--json", "isDraft", "--jq", ".isDraft"],
        capture_output=True, text=True, cwd=КОРЕНЬ)
    if вышло.returncode != 0:
        raise SystemExit(
            f"There's no release {метка} on GitHub yet. Push the tag first "
            "and wait for the Release workflow to make the draft.\n"
            + вышло.stderr.strip())
    if вышло.stdout.strip() != "true":
        raise SystemExit(f"Release {метка} is already published — not touching it.")


def суммы_с_маком(старые: str, архив: Path) -> str:
    """`SHA256SUMS.txt` черновика с новой строкой для маковского архива.

    Прочие строки (виндовая) остаются как были: их считал GitHub,
    и пересчитывать чужое здесь нечем и незачем.
    """
    сумма = hashlib.sha256(архив.read_bytes()).hexdigest()
    строки = [с for с in старые.splitlines()
              if с.strip() and not с.rstrip().endswith(АРХИВ)]
    строки.append(f"{сумма}  {АРХИВ}")
    return "\n".join(sorted(строки, key=lambda с: с.split()[-1])) + "\n"


def main(аргументы=None) -> int:
    разбор = argparse.ArgumentParser(
        description="Build the notarized Mac release from a tag and put it "
        "into that tag's draft release")
    разбор.add_argument("метка", metavar="tag", help="e.g. v0.2.1")
    это = разбор.parse_args(аргументы)
    метка = это.метка
    if sys.platform != "darwin":
        raise SystemExit("The Mac release is built on a Mac.")
    if shutil.which("gh") is None:
        raise SystemExit("No `gh` — GitHub's command line tool is needed "
                         "to put the archive into the draft.")

    репо = репозиторий()
    черновик_ли(метка, репо)
    выполнить(["git", "fetch", "--quiet", "origin", "tag", метка], cwd=КОРЕНЬ)

    врем = Path(tempfile.mkdtemp(prefix="vertcut-release-"))
    код = врем / "code"
    try:
        выполнить(["git", "worktree", "add", "--quiet", "--detach",
                   str(код), метка], cwd=КОРЕНЬ)
        выполнить([sys.executable, str(код / "install" / "build-release.py"),
                   "--notarize", "--out", str(врем)])
        архив = врем / АРХИВ

        выполнить(["gh", "release", "download", метка, "--repo", репо,
                   "--pattern", СУММЫ,
                   "--dir", str(врем), "--clobber"], cwd=КОРЕНЬ)
        суммы = врем / СУММЫ
        суммы.write_text(суммы_с_маком(суммы.read_text(encoding="utf-8"), архив),
                         encoding="utf-8")
        выполнить(["gh", "release", "upload", метка, "--repo", репо,
                   str(архив), str(суммы), "--clobber"], cwd=КОРЕНЬ)
        print(f"\n{АРХИВ} is in the draft of {метка}, notarized; "
              f"{СУММЫ} updated:\n{суммы.read_text(encoding='utf-8')}")
        print("Before publishing: download it from the draft and open it "
              "on a Mac with a double-click.")
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(код)],
                       cwd=КОРЕНЬ, capture_output=True)
        shutil.rmtree(врем, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
