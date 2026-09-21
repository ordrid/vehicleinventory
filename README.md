# Vehicle Inventory System

A small web application for keeping track of a fleet of vehicles, written as a
Python final project. It is a classic server-rendered Flask app: every page is
a normal HTML page, there is no JavaScript framework, and the only JavaScript
in the whole project is the one-line `window.print()` on the Reports page.

**Stack:** Python 3.12 · Flask · Jinja2 · SQLAlchemy 2.x · psycopg 3 ·
Flask-WTF · Tailwind CSS v4 · Neon Postgres (SQLite locally) ·
deployed on Vercel.

## Features

| Page | What it does |
|---|---|
| **Login / Logout** | Session-based sign in. Every other page redirects here when you are not logged in. Passwords are stored as `werkzeug.security` hashes, never in plain text. |
| **Dashboard** | Total vehicles plus a count for each status, and links to every other function. |
| **Add Vehicle** | Validated form. A duplicate plate number gives a friendly message on the field instead of a database error. |
| **View Vehicles** | Table of all vehicles, 10 per page, sortable by plate, make or year. |
| **Search** | Case-insensitive partial match across plate number, make and model, with status and type filters. Searches are plain `GET` requests, so a result page can be bookmarked. |
| **Edit Vehicle** | The same form as Add, pre-filled, with the same validation rules. |
| **Delete Vehicle** | A confirmation page first; the deletion itself only happens on `POST`, so nothing can be deleted by following a link. |
| **Reports** | Counts by status, by vehicle type and by year acquired, a print-friendly stylesheet with a Print button, and a CSV export of every vehicle. |

Flash messages confirm every action, and there are custom 404 and 500 pages.

## Data model

**users** — `id`, `username` (unique), `password_hash`, `created_at`

**vehicles**

| Field | Type | Notes |
|---|---|---|
| `id` | int | primary key |
| `plate_number` | str | required, unique, stored trimmed and upper-cased |
| `make` | str | required, e.g. Toyota |
| `model` | str | required, e.g. Hilux |
| `year` | int | required, 1950 to next year |
| `vehicle_type` | str | Sedan, SUV, Pickup, Van, Truck, Motorcycle |
| `color` | str | optional |
| `status` | str | Available, In Use, Under Maintenance, Retired |
| `date_acquired` | date | optional |
| `remarks` | text | optional |
| `created_at` / `updated_at` | datetime | set automatically |

## Local setup

Requires [uv](https://docs.astral.sh/uv/). With no `DATABASE_URL` set the app
uses a local SQLite file (`inventory.db`), so you can run it with no database
to install.

```bash
uv sync                          # install dependencies into .venv
cp .env.example .env             # then edit SECRET_KEY

uv run flask --app app init-db        # create the tables
uv run flask --app app create-admin   # prompts for username and password
uv run flask --app app seed           # insert 15 sample vehicles

uv run flask --app app run            # http://127.0.0.1:5000
```

The three setup commands are ordinary Flask CLI commands. Tables are
deliberately **never** created when the app starts up, because on a serverless
host the app is imported on every cold start. To set up the production
database, run the same commands locally with `DATABASE_URL` pointing at Neon.

## CSS

Tailwind is used through the **standalone Tailwind CLI**, so Node and npm are
not needed anywhere. The CLI comes from the `pytailwindcss` dev dependency.

There is no component library. The interface is built from plain Tailwind
utilities plus a small set of project classes (`.card`, `.btn`, `.pill`,
`.field`, `.data-table`, `.nav-link`) defined in `input.css`, which keeps the
built stylesheet at roughly 31 KB.

```bash
# while working on templates
uv run tailwindcss -i inventory/static/src/input.css -o inventory/static/css/output.css --watch

# before committing
uv run tailwindcss -i inventory/static/src/input.css -o inventory/static/css/output.css --minify
```

`inventory/static/css/output.css` is **committed to Git** on purpose: Vercel
then needs no build step at all, it just serves the file.

The palette, fonts and component classes all live in `inventory/static/src/input.css`:
a dark navy sidebar, a light content area, blue primary actions, and four status
pill colours kept far apart in hue so they stay easy to tell apart, including
when printed.

The first `tailwindcss` run downloads the CLI binary. If that fails with an SSL
certificate error, point Python at your system CA bundle:

```bash
SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt uv run tailwindcss ...
```

## The login photograph

`inventory/static/img/login-car.{webp,jpg}` is a photo by
[Olav Tvedt](https://unsplash.com/@olavtvedt) from
[Unsplash](https://unsplash.com/photos/-oVaYMgBMbs), used under the
[Unsplash License](https://unsplash.com/license) (free to use, no attribution
required — credited here anyway).

The 4000x6000, 3.1 MB original was optimised with ImageMagick down to
1200x1800:

```bash
magick original.jpg -auto-orient -resize 1200x1800^ -strip \
  -interlace Plane -sampling-factor 4:2:0 -quality 80 \
  inventory/static/img/login-car.jpg

magick original.jpg -auto-orient -resize 1200x1800^ -strip \
  -quality 76 -define webp:method=6 \
  inventory/static/img/login-car.webp
```

That gives a 52 KB WebP with a 139 KB JPEG fallback — 98% smaller than the
original. The page uses a `<picture>` element so browsers pick whichever they
support.

## Tests

```bash
uv run pytest
```

26 tests run against an in-memory SQLite database and cover login success and
failure, adding a vehicle (including the duplicate-plate and year-range
errors), viewing and paginating and sorting the list, searching and filtering,
editing, deleting, and the reports page and CSV export.

## Deploying to Vercel (Hobby tier)

1. Create a Postgres database at [neon.tech](https://neon.tech) and copy the
   **pooled** connection string (its host contains `-pooler`).
2. Push this repository to GitHub and import it at
   [vercel.com/new](https://vercel.com/new). No build command or framework
   preset is needed: Vercel finds the `app` object in the top-level `app.py`.
3. Add two environment variables in the Vercel project settings:
   - `DATABASE_URL` — the pooled Neon connection string
   - `SECRET_KEY` — a long random string
4. Deploy.
5. Create the tables and the first account by running the CLI commands from
   your own machine with `DATABASE_URL` set to the same Neon URL:

   ```bash
   DATABASE_URL='postgresql://...-pooler.../neondb?sslmode=require' \
     uv run flask --app app init-db
   ```

`requirements.txt` is generated with
`uv export --no-hashes --no-dev > requirements.txt` and committed as a fallback
for hosts that do not read `uv.lock`.

### Why the database is configured the way it is

`inventory/db.py` normalises `postgres://` and `postgresql://` URLs to
`postgresql+psycopg://` so the psycopg 3 driver is used, and builds the engine
with `poolclass=NullPool` and `pool_pre_ping=True`. Serverless functions are
short-lived and must not hold connections open between requests, and
`pool_pre_ping` throws away a connection Neon has already closed instead of
raising an error on the next query.

## Project layout

```
app.py                       entry point: exposes `app` for Vercel
inventory/
  __init__.py                app factory, config, blueprints, error pages
  db.py                      engine, sessions, get_database_url()
  models.py                  User and Vehicle
  forms.py                   LoginForm, VehicleForm, DeleteForm
  auth.py                    login, logout, @login_required
  vehicles.py                dashboard, CRUD and search routes
  reports.py                 reports page and CSV export
  cli.py                     init-db, create-admin, seed
  templates/                 base.html, one template per page, partials/
  static/
    src/input.css            Tailwind source: theme tokens + component classes
    css/output.css           built and committed
tests/                       pytest suite (in-memory SQLite)
```
