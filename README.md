# SwiftShipLogistics

A Django website for an international delivery and shipping company (headquartered in the UK, operating worldwide).

## Features

- **Accounts**: register, log in, log out. Each user gets a personal dashboard (shipment stats, account details, their shipments).
- **Shipment request form**: customers describe the goods or service, pick-up and destination (country, city, address) and the receiver. On submit they get a unique **tracking ID** (format `SSL-XXXXXXXXXX`).
- **Tracking page** (`/track/<ID>/`): current status, progress bar, full history written by your admins, and a **map** with the route travelled (solid line) and the remaining route (dashed line), plus a pulsing marker at the current location.
- **Admin panel** (`/admin/`): staff add a tracking update each time the goods move. The newest update automatically sets the shipment status shown to the customer.

## Setup

Requires Python 3.10+.

```bash
cd SwiftShipLogistics
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py makemigrations accounts shipments
python manage.py migrate
python manage.py createsuperuser   # this is your admin login
python manage.py runserver
```

Open http://127.0.0.1:8000/ and the admin at http://127.0.0.1:8000/admin/.

Optional check: `python manage.py test`

> `makemigrations` is part of setup because migration files are generated from the models on your machine. Commit the generated `migrations/` files afterwards.

## How admins update a shipment

1. Go to **Admin → Shipments** and open the shipment (search by tracking ID).
2. In the **Shipment updates** section at the bottom, fill in a new row:
   - **Status** (in transit, customs, delivered, etc.)
   - **Location** text shown to the customer, e.g. "Frankfurt Cargo Hub"
   - **Country** (places the map marker at that country's capital if no coordinates are given)
   - **Latitude / Longitude** (optional but recommended for an exact marker; right-click a spot on Google Maps to copy the numbers)
   - **Note** for the customer
3. Optionally set the **Estimated delivery** date, then save.

The customer's tracking page and map update immediately. Once an update has status **Delivered**, the page shows the shipment as completed.

## Project layout

```
manage.py
swiftship/        settings, root urls, wsgi/asgi
accounts/         registration + login/logout
shipments/        models, form, views, admin, country list (geo.py), tests
templates/        all HTML (base, home, accounts/, shipments/, partials/)
static/           css/style.css, js/track-map.js
```

## Customising

- **Countries**: edit `shipments/geo.py` (name → approximate latitude/longitude). New entries appear in the form and admin automatically.
- **Statuses**: edit `Shipment.Status` and `PROGRESS_STEPS` in `shipments/models.py`, plus the matching `.badge.<status>` colours in `static/css/style.css`.
- **Branding**: colours are CSS variables at the top of `static/css/style.css`.

## Going live

Set these environment variables:

```
DJANGO_SECRET_KEY=<a long random string>
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

Then run `python manage.py collectstatic`, serve with gunicorn/uvicorn behind nginx (or use a host like Render, Railway or PythonAnywhere), and consider PostgreSQL instead of SQLite. With `DJANGO_DEBUG=0` the site forces HTTPS; set `DJANGO_SSL_REDIRECT=0` to test locally over plain HTTP.

## Notes and limits

- The map needs internet access in the visitor's browser (Leaflet and OpenStreetMap tiles load from their public servers).
- Map positions are as precise as what admins enter. Without latitude/longitude the marker sits at the country's capital.
- Tracking pages are public by ID (so receivers can follow a parcel). Addresses, descriptions and receiver details are only shown to the owner and staff.
- Not included yet: email notifications, payments/pricing, password reset by email. These are natural next additions.
"# swift_shift" 
