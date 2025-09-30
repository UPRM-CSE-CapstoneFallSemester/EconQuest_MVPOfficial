# run_locust.py
"""
Convenience runner for Locust, ideal for PyCharm (Run/Debug).
You can tweak defaults via env vars without touching code:
  ECONQUEST_HOST (default: http://localhost:5000)
  USERS          (default: 200)
  SPAWN_RATE     (default: 20)
  DURATION       (default: 10m)
  LOCUST_EMAIL   (default: student@econquest.local)
  LOCUST_PASSWORD(default: student123)
"""
import os
import subprocess
import sys

def main():
    host = os.getenv("ECONQUEST_HOST", "http://localhost:5000")
    users = os.getenv("USERS", "200")
    spawn_rate = os.getenv("SPAWN_RATE", "20")
    duration = os.getenv("DURATION", "1m")

    # Ensure Locust is installed
    try:
        result = subprocess.run(["locust", "-V"], capture_output=True, text=True)
        if result.returncode != 0:
            print("Locust is not installed or not on PATH.")
            sys.exit(result.returncode)
    except FileNotFoundError:
        print("Locust executable not found. Try: pip install locust")
        sys.exit(1)

    args = [
        "locust",
        "-f", "locustfile.py",
        "--headless",
        "-u", users,
        "-r", spawn_rate,
        "-t", duration,
        "--host", host,
        "--html", "locust_200u_report.html",
        "--csv", "locust_200u"
    ]
    print("Running:", " ".join(args))
    sys.exit(subprocess.call(args))

if __name__ == "__main__":
    main()
