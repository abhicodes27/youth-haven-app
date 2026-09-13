# Youth Haven: Emergency Resource Finder for Displaced Youth

Youth Haven is a Streamlit web application that helps young people facing
housing instability, emergency displacement, or homelessness quickly find
shelter, food, legal support, and crisis counseling — without creating an
account, entering personal information, or leaving a data trail.

## Project Motivation (Human-Centered Design)

Young people in crisis often need help in the moment, from whatever device
is at hand, and often in situations where privacy and safety are as
important as the resource itself. Youth Haven is built around a few
human-centered principles:

- **No accounts, no tracking.** The app never asks for a name, email, or
  location history, and stores nothing server-side about who visited or
  what they searched for.
- **Immediate, low-friction access.** Filters, a map, and a directory are
  visible on load — no sign-up flow stands between a user and help.
- **Safety first.** A **Quick Exit** control is always visible in the
  header. It instantly clears in-session state and redirects the browser
  to a neutral search engine, so the app can be left with one tap if
  someone needs to hide what they were viewing.
- **Dignity in design.** Copy is written to be warm and non-judgmental,
  and resources note whether support is confidential and whether walk-ins
  are welcome, so users can plan a visit that feels safe for them.

## Architecture

```
youth-haven-app/
├── app.py                # Streamlit application (UI, filtering, map, analytics)
├── data/
│   └── resources.json    # Static resource dataset (shelters, food, legal, crisis lines)
├── requirements.txt       # Python dependencies
└── README.md
```

- **Frontend/UI:** [Streamlit](https://streamlit.io/) renders the entire
  app as a single-page experience: a header with mission copy and the
  Quick Exit control, a sidebar of filters, and three tabs — **Find
  Resources**, **About & Coverage Stats**, and **Demo Data (not real)**.
  Sample/placeholder data is never mixed into the first two tabs; it only
  ever appears in the clearly-labeled Demo Data tab, so a real search
  can't accidentally surface a fictional listing.
- **Map:** [Folium](https://python-visualization.github.io/folium/) renders
  an interactive dark-themed map, embedded via
  [`streamlit-folium`](https://github.com/randyzwitch/streamlit-folium),
  with one marker per filtered resource and a popup showing name, address,
  hours, and phone.
- **Analytics:** [Plotly Express](https://plotly.com/python/plotly-express/)
  renders category distribution, city distribution, and walk-in
  availability charts from the same filtered dataset shown in the
  directory and on the map, so every tab stays consistent.
- **Data layer:** Resources are loaded from `data/resources.json` with
  `st.cache_data`, sanitized field-by-field (missing values fall back to
  safe defaults instead of raising errors), and coerced into a typed
  pandas DataFrame used by every view.

No database or external API calls are required. All state lives only in
the browser session for the duration of a visit and is cleared on Quick
Exit or when the tab is closed.

## Data Schema

Each entry in `data/resources.json` (under the top-level `"resources"`
array) follows this schema:

| Field                  | Type    | Description                                                        |
|------------------------|---------|----------------------------------------------------------------------|
| `id`                   | integer | Unique identifier                                                   |
| `name`                 | string  | Organization or program name                                        |
| `category`             | string  | One of: `Emergency Housing`, `Food Security`, `Legal Support`, `Crisis Counseling` |
| `address`              | string  | Street address                                                      |
| `city`                 | string  | City name                                                            |
| `phone`                | string  | Contact phone number                                                 |
| `operating_hours`      | string  | Human-readable hours (e.g. `"24/7"`, `"Mon-Fri 9:00 AM - 5:00 PM"`)  |
| `age_range`            | string  | Eligible age range (e.g. `"16-24"`, `"All Ages"`)                    |
| `walk_in_allowed`      | boolean | Whether people can access services without an appointment           |
| `confidential_support` | boolean | Whether the service guarantees confidential support                 |
| `cost`                 | string  | Plain-language cost/access note, e.g. `"Free"`, `"Insurance accepted"`, `"Fees apply"`, `"Cost unknown"` |
| `appointment_required` | boolean | Whether you need to call ahead / book before showing up (defaults to `true` if missing — the cautious assumption) |
| `referral_required`    | boolean | Whether a referral from another agency or professional is needed to access the service |
| `latitude`             | float   | Approximate latitude for map placement (see note below)             |
| `longitude`            | float   | Approximate longitude for map placement (see note below)            |
| `is_sample`            | boolean | `true` if this is placeholder/demo data, not a verified real-world resource |
| `source_url`           | string  | Link to the organization's official page confirming these details    |
| `last_verified`        | string  | `YYYY-MM-DD` date this entry's details were last checked against the source |

If `is_sample`, `source_url`, or `last_verified` is omitted from an entry,
the loader treats it as **unverified** (`is_sample: true` by default) rather
than silently displaying it as confirmed. Sample entries never appear in the
**Find Resources** or **About & Coverage Stats** tabs — they only render in
the separate **Demo Data (not real)** tab, each still carrying its own
"⚠️ Sample/demo data" warning there.

**What "✅ Verified" means, precisely.** It means the address and phone
number were checked against the organization's own official listing
(linked as `source_url`) as of the `last_verified` date. It does **not**
mean current availability, wait times, or your personal eligibility were
confirmed — the UI says this explicitly next to the badge, and you should
still call ahead. `last_verified` is a fixed date stored in the JSON at
data-entry time; the app never computes or displays "today" in its place,
so the date always reflects when a human (or an AI assistant, with a web
search) actually checked the listing — not when the page happened to load.

As of this writing, the dataset includes verified resources for Frisco,
Plano, McKinney, and Dallas, TX (each sourced from the organization's own
website), alongside placeholder Pacific Northwest entries kept for
demonstration purposes and clearly labeled as sample data. Before relying
on any entry, confirm details are current — organizations change hours,
addresses, and phone numbers. Report outdated entries by opening an issue
or updating `data/resources.json` directly.

**A note on map precision.** The `latitude`/`longitude` values for the
verified Texas entries were placed by hand from the street address (no
geocoding API was available when this dataset was built), so a pin can be
off by a block or two — treat the map as a rough locator, not a precision
GPS fix. The verified `address` string itself is authoritative. For that
reason, every resource — in the directory list and in its map popup —
also has a **🧭 Directions** link that hands the exact address to Google
Maps, which geocodes it live at click time. That link is accurate
regardless of this dataset's own coordinate precision; if you re-import
this data elsewhere, consider running the addresses through a proper
geocoder (e.g. Census Bureau or Nominatim) to tighten the stored
coordinates too. Note also that `address` should hold the street address
only (no city/state/zip) — the UI always appends `city` when displaying
or building a Directions link, so an address that already includes the
city would render as a duplicate (e.g. "..., Frisco, TX 75036, Frisco").

The loader in `app.py` fills in sensible defaults for any missing or
malformed field (e.g. `"Hours not listed"`, `walk_in_allowed: false`) and
drops entries with unusable coordinates from the map view only — they
still appear in the directory and analytics.

## Local Setup

**Requirements:** Python 3.9+

```bash
# 1. Clone the repository
git clone <your-fork-url>
cd youth-haven-app

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`.

To add or update resources, edit `data/resources.json` directly — no code
changes are required as long as new entries follow the schema above.

## Deployment Guide

### Streamlit Community Cloud (recommended for quick deployment)

1. Push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in.
3. Click **New app**, select the repository/branch, and set the main
   file path to `app.py`.
4. Deploy — Streamlit Cloud installs `requirements.txt` automatically.

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```

```bash
docker build -t youth-haven-app .
docker run -p 8501:8501 youth-haven-app
```

### Generic VM / server

```bash
pip install -r requirements.txt
streamlit run app.py --server.port 80 --server.address 0.0.0.0
```

Put the app behind HTTPS (e.g. via a reverse proxy such as nginx or
Caddy) in any production deployment, since users may be accessing it from
shared or public devices where connection privacy matters.

## Privacy Notes

- The application itself does not ask for a name, create accounts, use
  tracking cookies, or persist filter selections beyond the current
  session — this is enforced in code (`app.py` has no database, file
  write, or analytics call in the request path).
- That said, this app cannot promise total anonymity, and the UI says so:
  Streamlit Community Cloud (or whatever host runs it) and the visitor's
  own network/ISP can see that the page was requested, the same as any
  website. The map's OpenStreetMap tiles are a third-party embed and may
  log those tile requests independently of this app.
- The dataset in `data/resources.json` mixes verified, sourced real-world
  resources (`is_sample: false`, with a `source_url` and `last_verified`
  date) with placeholder sample/demo entries (`is_sample: true`) kept for
  prototyping. The UI labels each accordingly — verified entries surface
  first, and sample entries carry an explicit "not a verified real-world
  resource" warning. Before using this app in a real community setting,
  verify every entry's current hours, eligibility, and contact details
  directly with the organization, and replace or remove remaining sample
  entries.
- Quick Exit clears Streamlit's session state and navigates away. Its
  on-screen label is deliberately literal — "Leaves this page. Does not
  erase browser history." — with no suggestion that private/incognito
  browsing is a substitute for that (it isn't: private browsing only
  prevents history from being written in the first place; it does nothing
  to history already recorded). Users in high-risk situations should be
  told plainly to also clear their browser history/tabs, or start a
  private/incognito session *before* visiting, if hiding this visit
  matters to them.
