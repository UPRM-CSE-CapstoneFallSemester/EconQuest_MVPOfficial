# run_locust.py
"""
Convenience runner for Locust, ideal for PyCharm (Run/Debug).

Env vars (all optional):
  ECONQUEST_HOST   default: http://localhost:5000
  USERS            default: 200
  SPAWN_RATE       default: 20
  DURATION         default: 1m       (Locust format, e.g. 30s, 10m, 1h)
  TAGS             default: (unset)  (comma-separated, e.g. ui,quiz)
  HEADLESS         default: 1        (1=headless, 0=web UI)
  LOGLEVEL         default: info     (debug|info|warning|error)
  STOP_TIMEOUT     default: (unset)  (seconds to wait before stopping)
  CSV_PREFIX       default: auto timestamped
  HTML_REPORT      default: auto timestamped
  LOCUSTFILE       default: locustfile.py
  LOCUST_EMAIL     default: student@econquest.local
  LOCUST_PASSWORD  default: student123
  STEP_LOAD        default: 0        (1 to enable --step-load)
  STEP_USERS       default: 50       (users added per step when STEP_LOAD=1)
  STEP_TIME        default: 30s      (duration per step when STEP_LOAD=1)
  LOCUST_OPTS      default: (unset)  extra flags, e.g.: "--reset-stats --exclude-tags api"

Examples:
  # Headless con tags ui y quiz
  TAGS=ui,quiz USERS=300 SPAWN_RATE=30 DURATION=10m python run_locust.py

  # Con UI web para explorar
  HEADLESS=0 python run_locust.py
"""

import os
import shlex
import subprocess
import sys
from datetime import datetime

def _ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def main():
    host        = os.getenv("ECONQUEST_HOST", "http://localhost:5000")
    users       = os.getenv("USERS", "200")
    spawn_rate  = os.getenv("SPAWN_RATE", "20")
    duration    = os.getenv("DURATION", "1m")
    tags        = os.getenv("TAGS", "").strip()
    headless    = os.getenv("HEADLESS", "1").strip() not in ("0", "false", "False", "no")
    loglevel    = os.getenv("LOGLEVEL", "info")
    stop_timeout= os.getenv("STOP_TIMEOUT", "").strip()
    csv_prefix  = os.getenv("CSV_PREFIX", f"locust_{_ts()}")
    html_report = os.getenv("HTML_REPORT", f"{csv_prefix}.html")
    locustfile  = os.getenv("LOCUSTFILE", "locustfile.py")
    step_load   = os.getenv("STEP_LOAD", "0").strip() in ("1","true","True","yes")
    step_users  = os.getenv("STEP_USERS", "50")
    step_time   = os.getenv("STEP_TIME", "30s")
    locust_opts = os.getenv("LOCUST_OPTS", "").strip()

    # Ensure locust exists
    try:
        out = subprocess.run(["locust", "-V"], capture_output=True, text=True)
        if out.returncode != 0:
            print("Locust is not installed or not on PATH.")
            sys.exit(out.returncode)
    except FileNotFoundError:
        print("Locust executable not found. Try: pip install locust")
        sys.exit(1)

    args = ["locust", "-f", locustfile, "--host", host, "--loglevel", loglevel]

    if headless:
        args += ["--headless", "-u", users, "-r", spawn_rate, "-t", duration]
        # Reports
        args += ["--html", html_report, "--csv", csv_prefix]
    # else: UI mode (no headless flags; puedes abrir http://localhost:8089)

    if tags:
        # Soporta múltiples tags separados por coma
        for t in [t.strip() for t in tags.split(",") if t.strip()]:
            args += ["--tags", t]

    if step_load:
        args += ["--step-load", "--step-users", str(step_users), "--step-time", step_time]

    if stop_timeout:
        args += ["--stop-timeout", stop_timeout]

    # Extra flags crudos (por ejemplo: "--reset-stats --exclude-tags api")
    if locust_opts:
        args += shlex.split(locust_opts)

    print("Running:", " ".join(shlex.quote(a) for a in args))
    # Útil para verificar rápidamente los parámetros efectivos
    print(f"[cfg] HEADLESS={int(headless)} HOST={host} USERS={users} SPAWN_RATE={spawn_rate} "
          f"DURATION={duration} TAGS={tags or '-'} STEP_LOAD={int(step_load)} "
          f"CSV_PREFIX={csv_prefix} HTML={html_report}")

    sys.exit(subprocess.call(args))

if __name__ == "__main__":
    main()
