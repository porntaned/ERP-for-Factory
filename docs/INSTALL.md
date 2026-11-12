# Install guide

From nothing to the running demo on one machine, with synthetic data only. Commands are bash and
run in the order shown; every one runs without a prompt, so the CI job `install-guide` in
[`.github/workflows/foundation.yml`](../.github/workflows/foundation.yml) runs the same commands
on PostgreSQL 18.6 (the differences are marked `# CI-only:` there).

> **Windows:** ยังไม่ได้ทดสอบบน Windows (not tested on Windows). The commands are bash; WSL or Git
> Bash may work but nobody has checked.

## 1. What you need

Exact versions are in the [Version contract](DEVELOPMENT.md#version-contract); this page does not
repeat them.

- **Git** ([downloads](https://git-scm.com/downloads)).
- **uv** at the version in the Version contract
  ([installation](https://docs.astral.sh/uv/getting-started/installation/)). uv installs the
  pinned Python for you; you do not need Python yourself.
- **PostgreSQL** at the version in the Version contract, installed any way you like
  ([official downloads](https://www.postgresql.org/download/)), running, with a superuser you can
  log in as with `psql`. SQLite is not supported.
- `openssl`, only to generate the secret key in step 2 (or type any long random value instead).

```bash
git --version
uv --version
```

## 2. Choose local values

Every value is yours to choose and stays on your machine; use synthetic values only. Use letters,
digits, `-` and `_` only (the commands below put them into `.env` with `sed`). The `PG*` variables
are the standard [libpq variables](https://www.postgresql.org/docs/current/libpq-envars.html) for
your **superuser** connection; `PGHOST` and `PGPORT` are also written into `.env` for the app.

```bash
export PGHOST=127.0.0.1
export PGPORT=5432
export PGUSER=postgres
export PGPASSWORD='replace-with-your-superuser-password'
export ERP_DB_PASSWORD='replace-with-a-local-db-password'
export ERP_SECRET_KEY="$(openssl rand -hex 32)"
export ERP_DEMO_PASSWORD='replace-with-a-demo-password'
```

`ERP_DEMO_PASSWORD` needs at least 8 characters. Keep this shell open: later steps read these
variables.

## 3. Create the database role and database

Run as the PostgreSQL superuser. The role gets `CREATEDB` because pytest-django creates and drops
its own test database (`test_erp_factory`) on every test run.

```bash
psql -d postgres -tAc 'SHOW server_version'
psql -v ON_ERROR_STOP=1 -v db_password="$ERP_DB_PASSWORD" -d postgres <<'SQL'
CREATE ROLE erp_factory LOGIN CREATEDB PASSWORD :'db_password';
CREATE DATABASE erp_factory OWNER erp_factory;
SQL
```

The first command prints the server version; it should match the Version contract. If your
superuser can only log in through the local socket (for example Debian/Ubuntu packages), put
`sudo -u postgres` in front of both `psql` commands instead of setting `PGUSER` and `PGPASSWORD`;
keep `PGHOST` and `PGPORT` for `.env`.

## 4. Get the code and write `.env`

```bash
git clone https://github.com/porntaned/ERP-for-Factory.git
cd ERP-for-Factory
sed -e "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$ERP_SECRET_KEY|" \
  -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$ERP_DB_PASSWORD|" \
  -e "s|^POSTGRES_HOST=.*|POSTGRES_HOST=$PGHOST|" \
  -e "s|^POSTGRES_PORT=.*|POSTGRES_PORT=$PGPORT|" \
  .env.example > .env
```

`.env` keeps `POSTGRES_DB=erp_factory`, `POSTGRES_USER=erp_factory` and `DJANGO_DEBUG=false` from
`.env.example`; every `replace-with-…` placeholder is replaced. `.env` is ignored by Git; never
commit it. The variables are described in
[Configuration boundary](DEVELOPMENT.md#configuration-boundary).

## 5. Install Python and dependencies

```bash
uv python install 3.14.8
uv sync --locked --all-groups
uv run python --version
```

The last command prints `Python 3.14.8`.

## 6. Check, migrate and test

```bash
uv run --env-file .env python manage.py check
uv run --env-file .env python manage.py migrate
uv run --env-file .env pytest
```

`check` prints `System check identified no issues (0 silenced).`. The full suite runs against
PostgreSQL in its own test database and takes a few minutes; it must end with every test passed.

## 7. Load the demo data

```bash
uv run --env-file .env python manage.py seed_demo
uv run --env-file .env python manage.py seed_production_demo
printf '%s\n' "$ERP_DEMO_PASSWORD" | uv run --env-file .env python manage.py set_demo_passwords --password-stdin
```

Both seeds go through the real Inventory, Quality and Manufacturing commands with fixed request
keys, so running them again adds nothing. `set_demo_passwords` gives the four `demo-*` users the
password in `ERP_DEMO_PASSWORD` (without `--password-stdin` it prompts twice).

## 8. Run and log in

```bash
DJANGO_DEBUG=true uv run --env-file .env python manage.py runserver
```

Open <http://127.0.0.1:8000/accounts/login/> and log in as `demo-warehouse` with
`ERP_DEMO_PASSWORD`. The balance page (**ยอดคงเหลือ**) lists the seeded stock, including the row
`LED-CHIP · L-0001 · RM-A · 100 · RELEASED`. Stop the server with Ctrl+C.

### Who sees what

Every logged-in user sees **ยอดคงเหลือ** (`/`), **การผลิต** (`/production/`, read only),
**ค้นหา Lot** (`/lots/search/`), Lot trace and genealogy pages, and **ประวัติ** (`/history/`).
The roles come from the seeds:

| User | Roles (warehouses) | Also sees |
|---|---|---|
| `demo-warehouse` | WAREHOUSE (RM-A, RM-B) | **รับเข้า** (`/receipts/new/`), **โอน** (`/transfers/new/`) |
| `demo-quality` | QUALITY (RM-A, RM-B, FG) | **คุณภาพ** (`/quality/`), **ประวัติ QC** (`/quality/audit/`) |
| `demo-approver` | APPROVER (RM-A, RM-B, LINE-1, FG) | **คุณภาพ** (return REJECTED to HOLD), **ประวัติ QC**, reverse buttons on **ประวัติ / กลับรายการ** and on production orders, **Scrap** |
| `demo-production` | PRODUCTION (RM-A, RM-B, LINE-1, FG) | **สร้าง order** (`/production/new/`) and the record buttons on an open order |

A screen a user may not use answers 403. The admin (`/admin/`) is read only and needs a superuser
you create yourself with `createsuperuser`; the demo users cannot open it.

### Walkthroughs

The data you now have is the starting point of the walkthroughs in
[DEVELOPMENT.md](DEVELOPMENT.md); follow them there:
[Inventory (M4.7)](DEVELOPMENT.md#inventory-demo-walkthrough-m47),
[Production (M5.4, M5.5)](DEVELOPMENT.md#production-demo-walkthrough-m54),
[Lot trace (M6.3)](DEVELOPMENT.md#lot-trace-m63-issue-108),
[Quality inspection (M6.1)](DEVELOPMENT.md#quality-inspection-m61-shell),
[REJECTED Lots (M6.2)](DEVELOPMENT.md#a-rejected-lot-is-unusable-everywhere-m62-issue-103) and
[QC history (M6.4)](DEVELOPMENT.md#qc-history-m64-issue-113).

## 9. Start the demo data again

> **Warning:** `--reset` flushes **every table** of the database in `.env` (all users, stock and
> history), not only the demo rows. Use it only on a disposable database such as the one made in
> step 3. `seed_demo --reset` does the same flush.

```bash
uv run --env-file .env python manage.py seed_production_demo --reset
printf '%s\n' "$ERP_DEMO_PASSWORD" | uv run --env-file .env python manage.py set_demo_passwords --password-stdin
```

The flush removes the demo users' passwords too, so the second command sets them again.

## Troubleshooting

Only problems actually met while checking this guide are listed.

- `uv python install 3.14.8` fails with
  `error: No download found for request: cpython-3.14.8-linux-x86_64-gnu`: your uv is older than
  the Version contract and does not know Python 3.14.8 (seen with uv 0.11.32). Install the uv
  version from the Version contract and run the command again.
