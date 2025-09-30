# EconQuest (MVP) Official

Bilingual, game-style micro-simulations for financial literacy. Flask + SQLite + Jinja.  
Roles: **student**, **teacher**, **admin**.

---

## Requirements
- Python **3.12**
- Git
- (Optional) PyCharm (use the project’s `.venv` as interpreter)

---

## Quick start (Windows / PowerShell)

```ps1
git clone https://github.com/<your-user>/EconQuest_MVP.git
cd EconQuest_MVP

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env          # luego puedes editar claves si deseas

flask --app run.py db upgrade   # crea la base de datos (SQLite en /instance)
flask --app run.py seed         # usuarios de demo y datos básicos
