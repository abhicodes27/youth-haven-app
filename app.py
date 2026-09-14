"""Youth Haven: Emergency Resource Finder for Displaced Youth."""

import json
import re
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import quote

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

DATA_PATH = Path(__file__).parent / "data" / "resources.json"

CATEGORY_COLORS = {
    "Emergency Housing": "red",
    "Food Security": "green",
    "Legal Support": "blue",
    "Crisis Counseling": "purple",
}

REQUIRED_FIELDS = [
    "id", "name", "category", "address", "city", "zip_code", "phone",
    "operating_hours", "age_range", "walk_in_allowed",
    "confidential_support", "cost", "appointment_required",
    "referral_required", "latitude", "longitude",
    "is_sample", "source_url", "last_verified", "is_verified",
]

DEFAULTS = {
    "name": "Unnamed Resource",
    "category": "Uncategorized",
    "address": "Address not available",
    "city": "Unknown",
    "zip_code": "",
    "phone": "Not listed",
    "operating_hours": "Hours not listed",
    "age_range": "All Ages",
    "walk_in_allowed": False,
    "confidential_support": False,
    "cost": "Cost unknown",
    # Missing access info defaults to the more cautious assumption.
    "appointment_required": True,
    "referral_required": False,
    "latitude": None,
    "longitude": None,
    # Missing provenance is treated as unverified, not silently trusted.
    "is_sample": True,
    "source_url": "",
    "last_verified": "",
}


st.set_page_config(
    page_title="Youth Haven | Emergency Resource Finder",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* ---------- Theme ---------- */
    :root {
        --yh-bg: #0B0F17;
        --yh-panel: rgba(255, 255, 255, 0.03);
        --yh-border: rgba(255, 255, 255, 0.10);
        --yh-text: #F1F5F9;
        --yh-muted: #B0BDCF;
        --yh-blue: #3B82F6;
        --yh-green: #10B981;
        --yh-red: #FF4655;
        --yh-radius: 20px;
        --yh-font: "Inter", system-ui, -apple-system,
                   BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    html {
        color-scheme: dark;
    }

    .stApp {
        background:
            radial-gradient(
                ellipse at 85% 0%,
                rgba(59, 130, 246, 0.08),
                transparent 42%
            ),
            radial-gradient(
                ellipse at 15% 70%,
                rgba(16, 185, 129, 0.035),
                transparent 40%
            ),
            var(--yh-bg);
        color: var(--yh-text);
        font-family: var(--yh-font);
    }

    .stApp :is(h1, h2, h3, h4, p, label, input, textarea, button) {
        font-family: var(--yh-font);
    }

    .stApp :is(h1, h2, h3, h4) {
        color: var(--yh-text);
        letter-spacing: -0.035em;
    }

    .stApp h1 {
        font-size: clamp(2rem, 4vw, 3.25rem);
        font-weight: 750;
        line-height: 1.12;
    }

    .stApp p {
        line-height: 1.65;
    }

    [data-testid="stCaptionContainer"] p {
        color: var(--yh-muted);
        font-size: 0.875rem;
    }

    [data-testid="stMainBlockContainer"],
    .main .block-container {
        max-width: 1280px;
        padding: 3rem 2.5rem 4rem;
    }

    /* Hide Streamlit chrome while preserving sidebar access. */
    [data-testid="stHeader"] {
        background: transparent;
        visibility: hidden;
    }

    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stExpandSidebarButton"],
    [data-testid="collapsedControl"] {
        visibility: visible !important;
        color: var(--yh-text);
        background: var(--yh-bg);
    }

    #MainMenu,
    footer,
    [data-testid="stToolbar"],
    [data-testid="stDecoration"] {
        display: none !important;
    }

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] {
        background: rgba(13, 19, 30, 0.96);
        border-right: 1px solid var(--yh-border);
    }

    [data-testid="stSidebarContent"] {
        padding-top: 1.25rem;
    }

    [data-testid="stWidgetLabel"] p {
        color: #DCE5F1;
        font-weight: 550;
        font-size: 0.9rem;
    }

    /* ---------- Inputs ---------- */
    [data-testid="stTextInput"] [data-baseweb="input"],
    [data-testid="stNumberInput"] [data-baseweb="input"],
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
        background: rgba(255, 255, 255, 0.035) !important;
        border: 1px solid var(--yh-border) !important;
        border-radius: 12px !important;
        transition: border-color 180ms ease, box-shadow 180ms ease;
    }

    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stMultiSelect"] input {
        color: var(--yh-text) !important;
        caret-color: #93C5FD;
        background: transparent !important;
    }

    .stApp input::placeholder {
        color: #91A0B5;
        opacity: 1;
    }

    [data-testid="stTextInput"]:focus-within [data-baseweb="input"],
    [data-testid="stNumberInput"]:focus-within [data-baseweb="input"],
    [data-testid="stMultiSelect"]:focus-within [data-baseweb="select"] > div {
        border-color: rgba(59, 130, 246, 0.8) !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
    }

    [data-testid="stMultiSelect"] [data-baseweb="tag"] {
        background: rgba(59, 130, 246, 0.15) !important;
        color: #BFDBFE !important;
        border: 1px solid rgba(59, 130, 246, 0.25);
        border-radius: 999px !important;
    }

    /* ---------- Glass cards ---------- */
    /* The key selector styles your resource containers directly. */
    [class*="st-key-resource_"],
    .yh-card,
    [data-testid="stMetric"],
    [data-testid="stExpander"] {
        background: var(--yh-panel);
        border: 1px solid var(--yh-border);
        border-radius: var(--yh-radius);
        -webkit-backdrop-filter: blur(10px);
        backdrop-filter: blur(10px);
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.12);
        transition:
            transform 180ms ease,
            border-color 180ms ease,
            box-shadow 180ms ease;
    }

    [class*="st-key-resource_"],
    .yh-card {
        padding: 1.4rem;
        margin-bottom: 0.9rem;
        position: relative;
        isolation: isolate;
    }

    /* A subtle gradient stroke without obscuring card contents. */
    [class*="st-key-resource_"]::before,
    .yh-card::before {
        content: "";
        position: absolute;
        inset: -1px;
        border-radius: inherit;
        padding: 1px;
        background: linear-gradient(
            125deg,
            rgba(59, 130, 246, 0.45),
            rgba(255, 255, 255, 0.06) 45%,
            rgba(16, 185, 129, 0.22)
        );
        -webkit-mask:
            linear-gradient(#fff 0 0) content-box,
            linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask:
            linear-gradient(#fff 0 0) content-box,
            linear-gradient(#fff 0 0);
        mask-composite: exclude;
        pointer-events: none;
    }

    [data-testid="stExpander"] details {
        border: 0 !important;
        background: transparent;
    }

    [data-testid="stExpander"] summary {
        min-height: 48px;
        color: var(--yh-text);
    }

    [data-testid="stMetric"] {
        padding: 1.25rem 1.5rem;
    }

    [data-testid="stMetricLabel"] p {
        color: var(--yh-muted);
        font-size: 0.875rem;
    }

    [data-testid="stMetricValue"] {
        color: #F8FAFC;
        font-weight: 700;
        letter-spacing: -0.045em;
    }

    /* ---------- Buttons ---------- */
    [data-testid="stButton"] button,
    [data-testid="stLinkButton"] a,
    .yh-button {
        min-height: 44px;
        border: 1px solid var(--yh-border);
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.04);
        color: var(--yh-text);
        font-weight: 600;
        text-decoration: none;
        transition:
            transform 180ms ease,
            background 180ms ease,
            border-color 180ms ease,
            box-shadow 180ms ease;
    }

    /* Your current Quick Exit uses type="primary". */
    [data-testid="stButton"] button[kind="primary"],
    .st-key-quick_exit button {
        background: linear-gradient(135deg, #E93648, #D9213C);
        color: #FFFFFF;
        border-color: rgba(255, 125, 135, 0.55);
        box-shadow:
            0 0 20px rgba(255, 70, 85, 0.19),
            inset 0 1px 0 rgba(255, 255, 255, 0.16);
    }

    /* ---------- Tabs ---------- */
    [data-baseweb="tab-list"] {
        gap: 0.35rem;
        border-bottom: 1px solid var(--yh-border);
    }

    [data-baseweb="tab"] {
        min-height: 46px;
        padding-inline: 1rem;
        color: var(--yh-muted);
        border-radius: 10px 10px 0 0;
    }

    [data-baseweb="tab"][aria-selected="true"] {
        color: #BFDBFE;
        background: rgba(59, 130, 246, 0.08);
    }

    [data-baseweb="tab-highlight"] {
        background: var(--yh-blue);
        height: 2px;
    }

    /* ---------- Reusable pill badges ---------- */
    .yh-badges {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 0.75rem 0;
    }

    .yh-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.35rem 0.75rem;
        border: 1px solid var(--yh-border);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.05);
        color: #DCE5F1;
        font-size: 0.8rem;
        font-weight: 550;
        line-height: 1.4;
    }

    .yh-badge--blue {
        color: #BFDBFE;
        background: rgba(59, 130, 246, 0.12);
        border-color: rgba(59, 130, 246, 0.3);
    }

    .yh-badge--green {
        color: #A7F3D0;
        background: rgba(16, 185, 129, 0.10);
        border-color: rgba(16, 185, 129, 0.28);
        box-shadow: 0 0 12px rgba(16, 185, 129, 0.06);
    }

    .yh-badge--verified {
        color: #C7D2FE;
        background: rgba(129, 140, 248, 0.10);
        border-color: rgba(129, 140, 248, 0.25);
    }

    /* ---------- Hover and keyboard focus ---------- */
    @media (hover: hover) and (pointer: fine) {
        [class*="st-key-resource_"]:hover,
        .yh-card:hover,
        [data-testid="stExpander"]:hover {
            transform: translateY(-2px);
            border-color: rgba(148, 163, 184, 0.32);
            box-shadow: 0 16px 42px rgba(0, 0, 0, 0.22);
        }

        [data-testid="stButton"] button:not(:disabled):hover,
        [data-testid="stLinkButton"] a:hover,
        .yh-button:hover {
            transform: translateY(-2px);
            border-color: rgba(147, 197, 253, 0.5);
        }

        [data-testid="stButton"] button[kind="primary"]:hover {
            border-color: #FDA4AF;
            box-shadow: 0 0 26px rgba(255, 70, 85, 0.30);
        }
    }

    .stApp :is(a, button, input, summary):focus-visible {
        outline: 3px solid #93C5FD !important;
        outline-offset: 3px;
    }

    /* ---------- Mobile and reduced motion ---------- */
    @media (max-width: 768px) {
        [data-testid="stMainBlockContainer"],
        .main .block-container {
            padding: 3.25rem 1rem 2rem;
        }

        [class*="st-key-resource_"],
        .yh-card {
            padding: 1rem;
            border-radius: 16px;
        }

        [data-baseweb="tab-list"] {
            flex-wrap: wrap;
        }

        .yh-badge {
            white-space: normal;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .stApp *,
        .stApp *::before,
        .stApp *::after {
            animation: none !important;
            transition: none !important;
            scroll-behavior: auto !important;
        }

        .stApp *:hover {
            transform: none !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def parse_age_range(age_range: str) -> tuple:
    """Convert an age_range string like '16-24' or 'All Ages' into a (min, max) tuple."""
    if not isinstance(age_range, str):
        return (0, 120)
    text = age_range.strip().lower()
    if "all" in text:
        return (0, 120)
    numbers = re.findall(r"\d+", text)
    if len(numbers) >= 2:
        return (int(numbers[0]), int(numbers[1]))
    if len(numbers) == 1:
        return (int(numbers[0]), 120)
    return (0, 120)


def directions_url(address: str, city: str) -> str:
    """Build a Google Maps search URL from the address text.

    This resolves the exact location at click-time from the verified
    address string, so navigation accuracy doesn't depend on this
    dataset's own (approximate) latitude/longitude fields.
    """
    query = f"{address}, {city}" if city and city not in address else address
    return f"https://www.google.com/maps/search/?api=1&query={quote(query)}"


def phone_digits(phone: str) -> str:
    """Extract a tel:-safe digit string (keeping a leading +) from a phone field."""
    return "".join(ch for ch in str(phone) if ch.isdigit() or ch == "+")


def format_verified_date(last_verified: str) -> str:
    """Render a stored YYYY-MM-DD date as 'Month D, YYYY'; falls back to the raw string."""
    if not last_verified:
        return ""
    try:
        return datetime.strptime(last_verified, "%Y-%m-%d").strftime("%B %-d, %Y")
    except ValueError:
        return last_verified


def apply_filters(
    df: pd.DataFrame,
    categories=None,
    location: str = "",
    age=None,
    walk_in_only: bool = False,
) -> pd.DataFrame:
    """Pure filtering function, kept separate from widgets so it's directly testable."""
    filtered = df.copy()
    if categories:
        filtered = filtered[filtered["category"].isin(categories)]
    if location:
        term = location.strip().lower()
        city_match = filtered["city"].str.lower().str.contains(term, na=False, regex=False)
        zip_match = filtered["zip_code"].astype(str).str.contains(term, na=False, regex=False)
        filtered = filtered[city_match | zip_match]
    if age is not None:
        filtered = filtered[(filtered["age_min"] <= age) & (filtered["age_max"] >= age)]
    if walk_in_only:
        filtered = filtered[filtered["walk_in_allowed"]]
    return filtered


@st.cache_data
def load_resources(path: Path) -> pd.DataFrame:
    """Load and sanitize the resource dataset, filling in gaps gracefully."""
    if not path.exists():
        return pd.DataFrame(columns=REQUIRED_FIELDS)

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return pd.DataFrame(columns=REQUIRED_FIELDS)

    records = raw.get("resources", []) if isinstance(raw, dict) else raw
    if not records:
        return pd.DataFrame(columns=REQUIRED_FIELDS)

    cleaned = []
    for i, rec in enumerate(records):
        item = dict(rec) if isinstance(rec, dict) else {}
        item.setdefault("id", i + 1)
        for field, default in DEFAULTS.items():
            if item.get(field) in (None, ""):
                item[field] = default
        cleaned.append(item)

    df = pd.DataFrame(cleaned)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["walk_in_allowed"] = df["walk_in_allowed"].astype(bool)
    df["confidential_support"] = df["confidential_support"].astype(bool)
    df["appointment_required"] = df["appointment_required"].astype(bool)
    df["referral_required"] = df["referral_required"].astype(bool)
    df["is_sample"] = df["is_sample"].astype(bool)
    age_bounds = df["age_range"].apply(parse_age_range)
    df["age_min"] = age_bounds.apply(lambda t: t[0])
    df["age_max"] = age_bounds.apply(lambda t: t[1])
    # A real (non-sample) row only counts as "Verified" if it actually
    # carries evidence — a source link and a verification date. A record
    # with is_sample: false but no source/date is neither sample data nor
    # properly verified, and must not silently pass as confirmed.
    has_source = df["source_url"].astype(str).str.strip() != ""
    has_date = df["last_verified"].astype(str).str.strip() != ""
    df["is_verified"] = (~df["is_sample"]) & has_source & has_date
    return df


def quick_exit():
    """Clear session state and redirect the browser to a neutral site."""
    st.session_state.clear()
    st.markdown(
        """
        <meta http-equiv="refresh" content="0; url=https://www.google.com">
        <script>
            window.location.replace("https://www.google.com");
        </script>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


def render_header():
    nav_left, nav_right = st.columns([5, 1])
    with nav_left:
        st.markdown(
            """
            <h1 style="margin-bottom:0;">🏠 Youth Haven</h1>
            <p style="font-size:1.05rem; color:#9ca3af; margin-top:0;">
            Emergency Resource Finder for Displaced Youth
            </p>
            """,
            unsafe_allow_html=True,
        )
    with nav_right:
        st.write("")
        if st.button(
            "🚪 Quick Exit",
            help="Leaves this page. Does not erase browser history.",
            use_container_width=True,
            type="primary",
            key="quick_exit",
        ):
            quick_exit()
        st.caption("Leaves this page. Does not erase browser history.")

    st.markdown(
        "**You are not alone.** Youth Haven helps you find shelter, food, "
        "legal aid, and crisis support near you — quickly, and without "
        "creating an account."
    )

    with st.expander("🔒 What this site does and doesn't do with your data"):
        st.markdown(
            """
            - This app does **not** ask for your name or create an account.
            - Your filter inputs (age, city/ZIP, category, search terms) are
              sent to and processed on the server — like any web app, that's
              how the results get computed — but this app does **not**
              intentionally write them to a database, log file, or analytics
              service. They exist only for the moment it takes to build your
              results, and are discarded when your session ends or you click
              **Quick Exit**.
            - This app does **not** use tracking cookies or analytics scripts.
            - That said, no website can promise total invisibility: the
              hosting provider and your network (Wi-Fi, ISP, or workplace)
              can typically see that you visited this page, the same as any
              site you load, and standard server infrastructure logs (request
              timestamps, IP addresses) are generally outside this app's
              control. The interactive map also loads map tiles from
              OpenStreetMap, an external service, which may log that
              request like any embedded image.
            - **Quick Exit** clears this app's session and sends you to
              Google — it does **not** erase your browser history. If you
              need to hide that you visited, use a private/incognito window
              and clear your history afterward.
            """
        )
    st.divider()


def render_filters(df: pd.DataFrame) -> dict:
    st.sidebar.header("🔎 Find What You Need")
    st.sidebar.caption(
        "Your filter inputs are processed temporarily on the server to build "
        "your results — this app does not intentionally save or log them "
        "anywhere. See the “What this site does with your data” section near "
        "the top of the page for the full picture, including what your "
        "network or hosting provider can still see."
    )

    known_cities = sorted(df["city"].dropna().unique().tolist()) if not df.empty else []
    known_zips = sorted(z for z in df["zip_code"].dropna().unique().tolist() if z) if not df.empty else []
    categories = sorted(df["category"].dropna().unique().tolist()) if not df.empty else []
    selected_categories = st.sidebar.multiselect("Category", options=categories, default=categories)

    location_input = st.sidebar.text_input(
        "Your city or ZIP code (optional)",
        value="",
        help=(
            "Matched against each resource's city name and ZIP code. "
            "Cities covered: " + (", ".join(known_cities) if known_cities else "none yet")
            + ". ZIP codes covered: " + (", ".join(known_zips) if known_zips else "none yet")
            + ". A ZIP near one of these but not listed won't match — it "
            "isn't a radius search."
        ),
    )

    age_input = st.sidebar.text_input(
        "Your age (optional)",
        value="",
        help="Enter your age and we'll only show resources you're eligible for.",
    )
    user_age = None
    if age_input.strip():
        try:
            user_age = int(age_input.strip())
        except ValueError:
            st.sidebar.warning("Please enter your age as a number.")

    walk_in_only = st.sidebar.checkbox("Walk-ins only", value=False)

    st.sidebar.divider()
    st.sidebar.markdown(
        "**In immediate danger?**\n\nCall or text **988** (Suicide & Crisis Lifeline)\n\n"
        "or **911** for emergencies."
    )

    filtered = apply_filters(
        df,
        categories=selected_categories,
        location=location_input.strip(),
        age=user_age,
        walk_in_only=walk_in_only,
    )

    return {
        "filtered": filtered,
        "location_input": location_input.strip(),
        "user_age": user_age,
        "known_cities": known_cities,
        "known_zips": known_zips,
        "selected_categories": selected_categories,
        "all_categories": categories,
        "walk_in_only": walk_in_only,
    }


def describe_no_results(filters: dict, known_cities=None, known_zips=None) -> str:
    """Build a specific, actionable empty-state message naming which active
    filters are narrowing the results and how to broaden each one."""
    known_cities = known_cities or []
    known_zips = known_zips or []
    location = filters.get("location_input") or ""
    age = filters.get("user_age")
    selected = filters.get("selected_categories") or []
    all_cats = filters.get("all_categories") or []
    walk_in_only = filters.get("walk_in_only", False)
    category_limited = bool(selected) and bool(all_cats) and set(selected) != set(all_cats)

    active = []
    if location:
        active.append(f'city/ZIP "{location}"')
    if age is not None:
        active.append(f"age {age}")
    if category_limited:
        active.append(f"category limited to {', '.join(sorted(selected))}")
    if walk_in_only:
        active.append('"Walk-ins only"')

    if not active:
        return "No resources match your current filters. Try adjusting them in the sidebar."

    msg = f"No resources match {', '.join(active)}. "
    suggestions = []
    if location:
        covers = []
        if known_cities:
            covers.append(f"cities: {', '.join(known_cities)}")
        if known_zips:
            covers.append(f"ZIP codes: {', '.join(known_zips)}")
        if covers:
            suggestions.append(f"try one of the covered {' / '.join(covers)}, or clear the city/ZIP field")
        else:
            suggestions.append("clear the city/ZIP field")
    if age is not None:
        suggestions.append("clear the age field to see options for other ages")
    if category_limited:
        suggestions.append("select more categories")
    if walk_in_only:
        suggestions.append('uncheck "Walk-ins only"')
    msg += "Try: " + "; ".join(suggestions) + "."
    return msg


def apply_text_search(df: pd.DataFrame, search_term: str) -> pd.DataFrame:
    """Pure name/city/address text search, kept separate so it can be reused
    identically for the card list, the displayed count, and the map."""
    if not search_term:
        return df
    term = search_term.lower()
    mask = (
        df["name"].str.lower().str.contains(term, na=False, regex=False)
        | df["city"].str.lower().str.contains(term, na=False, regex=False)
        | df["address"].str.lower().str.contains(term, na=False, regex=False)
    )
    return df[mask]


def render_directory(
    df: pd.DataFrame,
    location_input: str,
    known_cities=None,
    known_zips=None,
    key_prefix: str = "find",
    filters: dict = None,
) -> pd.DataFrame:
    """Renders the directory and returns the final filtered DataFrame (after
    the in-page text search) so callers can pass the identical data to the
    map — the card list, the displayed count, and the map must never
    disagree about which resources matched."""
    known_cities = known_cities or []
    known_zips = known_zips or []
    heading = f"📋 Resources Near \"{location_input}\"" if location_input else "📋 Available Resources"
    st.subheader(heading)

    if df.empty:
        msg = describe_no_results(filters or {}, known_cities, known_zips)
        st.warning(msg)
        return df

    search_term = st.text_input(
        "Search by name, city, or address", value="", key=f"{key_prefix}_search"
    )
    view = apply_text_search(df, search_term)

    st.markdown(f"{len(view)} resource(s) match your filters.")

    if view.empty:
        st.warning(
            f'No resources match "{search_term}". Try a different name, city, '
            "or address, or clear the search box above."
        )
        return view

    # Verified, sourced resources surface above unverified/sample entries.
    view = view.sort_values(by=["is_sample", "name"], ascending=[True, True])

    for _, row in view.iterrows():
        with st.container(
            border=False,
            key=f"resource_{key_prefix}_{row['id']}",
        ):
            col_info, col_action = st.columns([4, 1])
            with col_info:
                st.markdown(f"**{row['name']}**  \n*{row['category']}*")

                badges = []
                if str(row["operating_hours"]).strip() == "24/7":
                    badges.append('<span class="yh-badge yh-badge--blue">24/7 service</span>')
                if str(row["cost"]).strip().lower() == "free":
                    badges.append('<span class="yh-badge yh-badge--green">Free</span>')
                if row["is_verified"]:
                    badges.append(
                        '<span class="yh-badge yh-badge--verified">'
                        f"Last verified: {escape(str(row['last_verified']))}"
                        "</span>"
                    )
                if badges:
                    st.markdown(
                        '<div class="yh-badges">' + "".join(badges) + "</div>",
                        unsafe_allow_html=True,
                    )

                st.markdown(f"📍 {row['address']}, {row['city']}")
                st.markdown(f"🕒 {row['operating_hours']}  |  👥 Ages {row['age_range']}")
                st.markdown(f"💲 {row['cost']}")

                access_bits = []
                if row["walk_in_allowed"]:
                    access_bits.append("🚶 Walk-ins welcome")
                if row["appointment_required"]:
                    access_bits.append("📅 Appointment/call-ahead required")
                if row["referral_required"]:
                    access_bits.append("📄 Referral required")
                if row["confidential_support"]:
                    access_bits.append("🔒 Confidential support")
                if access_bits:
                    st.markdown(" · ".join(access_bits))

                if row["is_sample"]:
                    st.warning(
                        "⚠️ Sample/demo data for this prototype — not a "
                        "verified real-world resource. Do not rely on this "
                        "entry for actual help; call 211 or 988 instead.",
                        icon="⚠️",
                    )
                elif row["is_verified"]:
                    verified_date = format_verified_date(row["last_verified"])
                    short_line = "✅ Address and phone checked"
                    short_line += f" {verified_date}." if verified_date else "."
                    st.markdown(short_line)
                    st.markdown("📞 Call to confirm availability and eligibility.")
                    with st.expander(
                        "What does “Verified” mean?",
                        key=f"{key_prefix}_verified_expander_{row['id']}",
                    ):
                        detail = (
                            "We confirmed this resource's address and phone number "
                            "against its official listing"
                        )
                        detail += f" on {verified_date}." if verified_date else "."
                        detail += (
                            " This does **not** confirm current availability, wait "
                            "times, or your eligibility — please call ahead to check."
                        )
                        st.markdown(detail)
                        if row["source_url"]:
                            st.markdown(f"[Official source]({row['source_url']})")
                else:
                    st.warning(
                        "⚠️ Not verified: this entry is missing an official "
                        "source link and/or a verification date, so it is "
                        "**not** shown as confirmed. Do not rely on it "
                        "without independently checking the organization.",
                        icon="⚠️",
                    )
            with col_action:
                digits = phone_digits(row["phone"])
                if row["is_sample"]:
                    st.button(
                        "📞 Call (disabled — demo data)",
                        disabled=True,
                        use_container_width=True,
                        key=f"{key_prefix}_call_{row['id']}",
                        help="This is fictional sample data; calling it would not reach a real service.",
                    )
                    st.button(
                        "🧭 Directions (disabled — demo data)",
                        disabled=True,
                        use_container_width=True,
                        key=f"{key_prefix}_directions_{row['id']}",
                        help="This is fictional sample data; there is nowhere real to navigate to.",
                    )
                elif digits:
                    st.link_button(
                        "📞 Call",
                        f"tel:{digits}",
                        use_container_width=True,
                        key=f"{key_prefix}_call_{row['id']}",
                    )
                    st.link_button(
                        "🧭 Directions",
                        directions_url(row["address"], row["city"]),
                        use_container_width=True,
                        help="Opens the exact address in Google Maps for precise navigation.",
                        key=f"{key_prefix}_directions_{row['id']}",
                    )
                else:
                    st.button(
                        "📞 No phone",
                        disabled=True,
                        use_container_width=True,
                        key=f"{key_prefix}_nophone_{row['id']}",
                    )
                    st.link_button(
                        "🧭 Directions",
                        directions_url(row["address"], row["city"]),
                        use_container_width=True,
                        help="Opens the exact address in Google Maps for precise navigation.",
                        key=f"{key_prefix}_directions_{row['id']}",
                    )
    return view


def render_map(df: pd.DataFrame, location_input: str):
    heading = f"📍 Map of Resources Near \"{location_input}\"" if location_input else "📍 Map of All Resources"
    st.subheader(heading)
    st.markdown(
        "Pins are approximate placements based on each address, not a "
        "precision GPS geocode. Use a pin's popup, or the \"🧭 Directions\" "
        "button in the resource list, to get exact turn-by-turn navigation."
    )

    mappable = df.dropna(subset=["latitude", "longitude"])
    if mappable.empty:
        st.info("No mappable resources match your current filters. Try adjusting them in the sidebar.")
        return

    center_lat = mappable["latitude"].mean()
    center_lon = mappable["longitude"].mean()
    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles="OpenStreetMap",
    )

    for _, row in mappable.iterrows():
        color = CATEGORY_COLORS.get(row["category"], "gray")
        if row["is_sample"]:
            verification_html = "⚠️ Sample/demo data — not verified"
        elif row["is_verified"]:
            verification_html = f"✅ Verified as of {row['last_verified']}"
        else:
            verification_html = "⚠️ Not verified — missing source/date"
        maps_link = directions_url(row["address"], row["city"])
        popup_html = (
            f"<b>{row['name']}</b><br>"
            f"{row['category']}<br>"
            f"{row['address']}, {row['city']}<br>"
            f"Hours: {row['operating_hours']}<br>"
            f"Phone: {row['phone']}<br>"
            f"Cost: {row['cost']}<br>"
            f"Walk-ins: {'Yes' if row['walk_in_allowed'] else 'No'}<br>"
            f"{verification_html}<br>"
            f'<a href="{maps_link}" target="_blank" rel="noopener">🧭 Get exact directions</a>'
        )
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=row["name"],
            icon=folium.Icon(color=color, icon="info-sign"),
        ).add_to(fmap)

    st_folium(fmap, width=None, height=420, returned_objects=[])


def render_analytics(df: pd.DataFrame):
    st.subheader("📊 Project Coverage Stats")
    st.markdown(
        "This tab is about the dataset, not your personal search — it summarizes "
        "how many **verified** resources of each type are in Youth Haven's "
        "directory and where they're located, filtered by whatever you've "
        "selected in the sidebar. Sample/demo data is excluded from these stats."
    )

    if df.empty:
        st.info("No data available to display statistics for the current filters.")
        return

    col1, col2 = st.columns(2)

    with col1:
        category_counts = df["category"].value_counts().reset_index()
        category_counts.columns = ["category", "count"]
        fig_cat = px.bar(
            category_counts,
            x="category",
            y="count",
            color="category",
            title="Resources by Category",
            labels={"category": "Category", "count": "Number of Resources"},
        )
        fig_cat.update_layout(showlegend=False, template="plotly_dark")
        st.plotly_chart(fig_cat, use_container_width=True)

    with col2:
        city_counts = df["city"].value_counts().reset_index()
        city_counts.columns = ["city", "count"]
        fig_city = px.pie(
            city_counts,
            names="city",
            values="count",
            title="Resource Distribution by City",
            hole=0.4,
        )
        fig_city.update_layout(template="plotly_dark")
        st.plotly_chart(fig_city, use_container_width=True)

    st.markdown("#### Walk-in Availability by Category")
    walkin_summary = (
        df.groupby("category")["walk_in_allowed"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "walk_in", "count": "total"})
        .reset_index()
    )
    walkin_summary["no_walk_in"] = walkin_summary["total"] - walkin_summary["walk_in"]
    fig_walkin = px.bar(
        walkin_summary,
        x="category",
        y=["walk_in", "no_walk_in"],
        title="Walk-in vs. Appointment-Only Resources",
        labels={"value": "Number of Resources", "category": "Category", "variable": "Access Type"},
    )
    fig_walkin.update_layout(template="plotly_dark", legend_title_text="Access Type")
    st.plotly_chart(fig_walkin, use_container_width=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Resources", len(df))
    m2.metric("Walk-in Friendly", int(df["walk_in_allowed"].sum()))
    m3.metric("Confidential Support", int(df["confidential_support"].sum()))


def main():
    render_header()

    resources_df = load_resources(DATA_PATH)
    if resources_df.empty:
        st.error(
            "Resource data could not be loaded. Please confirm `data/resources.json` "
            "exists and is formatted correctly."
        )
        return

    real_df = resources_df[~resources_df["is_sample"]].copy()
    sample_df = resources_df[resources_df["is_sample"]].copy()

    filter_result = render_filters(real_df)
    filtered_df = filter_result["filtered"]
    location_input = filter_result["location_input"]
    known_cities = filter_result["known_cities"]
    known_zips = filter_result["known_zips"]

    tab_find, tab_about, tab_demo = st.tabs(
        ["🧭 Find Resources", "📊 About & Coverage Stats", "🧪 Demo Data (not real)"]
    )

    with tab_find:
        # render_directory returns the FINAL filtered set (sidebar filters +
        # the in-page text search), which the map below reuses — so the
        # count, the cards, and the map pins can never disagree.
        final_find_df = render_directory(
            filtered_df,
            location_input,
            known_cities,
            known_zips,
            key_prefix="find",
            filters=filter_result,
        )
        st.divider()
        with st.expander("🗺️ Show map (optional)", expanded=False):
            render_map(final_find_df, location_input)

    with tab_about:
        render_analytics(filtered_df)

    with tab_demo:
        st.warning(
            "⚠️ **Everything in this tab is fictional placeholder data** used "
            "to prototype this app's layout and features while real resources "
            "were being sourced. None of these are real organizations — do "
            "not contact them for help. For real help, use the **Find "
            "Resources** tab, or call **211** (general assistance) or **988** "
            "(crisis support).",
            icon="⚠️",
        )
        render_directory(
            sample_df,
            "",
            sorted(sample_df["city"].dropna().unique().tolist()),
            key_prefix="demo",
        )

    st.divider()
    st.caption(
        "Youth Haven does not create accounts or save your searches. "
        "If you are in immediate danger, call 911. For confidential crisis support, "
        "call or text 988."
    )


if __name__ == "__main__":
    main()
