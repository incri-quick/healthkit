"""Run one trial command against both snapshots; record time, exit code, output size.

Measurement only (slice 001). Not toolkit code: it will not be reused.

    python measure.py <label> -- <command...>

The command runs with the snapshot as its working directory. Output goes to
raw/<label>-<snapshot>.out and raw/<label>-<snapshot>.err. A summary line per
snapshot goes to stdout and is appended to raw/runs.tsv.
"""
import subprocess
import sys
import time
from pathlib import Path

SLICE = Path(__file__).resolve().parent
RAW = SLICE / "raw"
SNAPSHOTS = {
    "dev": Path(r"C:\Users\legio\Workspace\Integrated_RPA\quickrpa-integrated-backend"),
    "pre": Path(
        r"C:\Users\legio\AppData\Local\Temp\claude"
        r"\c--Users-legio-Workspace-Integrated-RPA-quickrpa-integrated-backend"
        r"\35db7486-60b1-461c-a7f9-303f23092bf4\scratchpad\qrpa-pre-review"
    ),
}


def main() -> None:
    label = sys.argv[1]
    command = sys.argv[sys.argv.index("--") + 1:]
    RAW.mkdir(exist_ok=True)
    for name, root in SNAPSHOTS.items():
        out_path = RAW / f"{label}-{name}.out"
        err_path = RAW / f"{label}-{name}.err"
        start = time.monotonic()
        with out_path.open("wb") as out, err_path.open("wb") as err:
            code = subprocess.call(command, cwd=root, stdout=out, stderr=err)
        seconds = time.monotonic() - start
        line = (
            f"{label}\t{name}\texit={code}\t{seconds:.1f}s\t"
            f"out={out_path.stat().st_size}B\terr={err_path.stat().st_size}B"
        )
        print(line)
        with (RAW / "runs.tsv").open("a", encoding="utf-8") as runs:
            runs.write(line + "\n")


if __name__ == "__main__":
    main()
