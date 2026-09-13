"""Youth Haven: Emergency Resource Finder for Displaced Youth."""

import json
import re
from pathlib import Path

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
    "id", "name", "category", "address", "city", "phone",
    "operating_hours", "age_range", "walk_in_allowed",
    "confidential_support", "latitude", "longitude",
]

DEFAULTS = {
    "name": "Unnamed Resource",
    "category": "Uncategorized",
    "address": "Address not available",
    "city": "Unknown",
    "phone": "Not listed",
    "operating_hours": "Hours not listed",
    "age_range": "All Ages",
    "walk_in_allowed": False,
    "confidential_support": False,
    "latitude": None,
    "longitude": None,
}


st.set_page_config(
    page_title="Youth Haven | Emergency Resource Finder",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
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
    age_bounds = df["age_range"].apply(parse_age_range)
    df["age_min"] = age_bounds.apply(lambda t: t[0])
    df["age_max"] = age_bounds.apply(lambda t: t[1])
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
            help="Clears your filters and this session, then leaves the site.",
            use_container_width=True,
            type="primary",
        ):
            quick_exit()
        st.caption("Doesn't clear browser history — use private browsing for that.")

    st.markdown(
        "**You are not alone.** Youth Haven helps you find shelter, food, "
        "legal aid, and crisis support near you — quickly, and without "
        "creating an account."
    )

    with st.expander("🔒 What this site does and doesn't do with your data"):
        st.markdown(
            """
            - This app does **not** ask for your name, create an account, or
              save your searches. Your filter choices live only in this
              browser tab and are cleared when you close it or click
              **Quick Exit**.
            - This app does **not** use tracking cookies or analytics scripts.
            - That said, no website can promise total invisibility: the
              hosting provider and your network (Wi-Fi, ISP, or workplace)
              can typically see that you visited this page, the same as any
              site you load. The interactive map also loads map tiles from
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
    st.sidebar.caption("Filters help narrow results. Nothing you select is stored or sent anywhere.")

    categories = sorted(df["category"].dropna().unique().tolist()) if not df.empty else []
    selected_categories = st.sidebar.multiselect("Category", options=categories, default=categories)

    location_input = st.sidebar.text_input(
        "Your city or ZIP code (optional)",
        value="",
        help="We currently match this against each resource's city name.",
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

    filtered = df.copy()
    if selected_categories:
        filtered = filtered[filtered["category"].isin(selected_categories)]
    if location_input.strip():
        term = location_input.strip().lower()
        filtered = filtered[filtered["city"].str.lower().str.contains(term, na=False)]
    if user_age is not None:
        filtered = filtered[(filtered["age_min"] <= user_age) & (filtered["age_max"] >= user_age)]
    if walk_in_only:
        filtered = filtered[filtered["walk_in_allowed"]]

    return {
        "filtered": filtered,
        "location_input": location_input.strip(),
        "user_age": user_age,
    }


def render_directory(df: pd.DataFrame, location_input: str):
    heading = f"📋 Resources Near \"{location_input}\"" if location_input else "📋 Available Resources"
    st.subheader(heading)
    st.caption(f"{len(df)} resource(s) match your filters.")

    if df.empty:
        st.warning("No resources match your current filters. Try adjusting them in the sidebar.")
        return

    search_term = st.text_input("Search by name, city, or address", value="")
    view = df.copy()
    if search_term:
        term = search_term.lower()
        mask = (
            view["name"].str.lower().str.contains(term, na=False)
            | view["city"].str.lower().str.contains(term, na=False)
            | view["address"].str.lower().str.contains(term, na=False)
        )
        view = view[mask]

    if view.empty:
        st.warning("No resources match your search.")
        return

    for _, row in view.iterrows():
        with st.container(border=True):
            col_info, col_action = st.columns([4, 1])
            with col_info:
                st.markdown(f"**{row['name']}**  \n*{row['category']}*")
                st.caption(f"📍 {row['address']}, {row['city']}")
                st.caption(f"🕒 {row['operating_hours']}  |  👥 Ages {row['age_range']}")
                badges = []
                if row["walk_in_allowed"]:
                    badges.append("🚶 Walk-ins welcome")
                if row["confidential_support"]:
                    badges.append("🔒 Confidential support")
                if badges:
                    st.caption(" · ".join(badges))
            with col_action:
                phone = row["phone"]
                digits = "".join(ch for ch in str(phone) if ch.isdigit() or ch == "+")
                if digits:
                    st.link_button("📞 Call", f"tel:{digits}", use_container_width=True)
                else:
                    st.button("📞 No phone", disabled=True, use_container_width=True, key=f"nophone_{row['id']}")


def render_map(df: pd.DataFrame, location_input: str):
    heading = f"📍 Map of Resources Near \"{location_input}\"" if location_input else "📍 Map of All Resources"
    st.subheader(heading)

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
        popup_html = (
            f"<b>{row['name']}</b><br>"
            f"{row['category']}<br>"
            f"{row['address']}, {row['city']}<br>"
            f"Hours: {row['operating_hours']}<br>"
            f"Phone: {row['phone']}<br>"
            f"Walk-ins: {'Yes' if row['walk_in_allowed'] else 'No'}"
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
    st.caption(
        "This tab is about the dataset, not your personal search — it summarizes "
        "how many resources of each type are in Youth Haven's directory and where "
        "they're located, filtered by whatever you've selected in the sidebar."
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

    filter_result = render_filters(resources_df)
    filtered_df = filter_result["filtered"]
    location_input = filter_result["location_input"]

    tab_find, tab_about = st.tabs(["🧭 Find Resources", "📊 About & Coverage Stats"])

    with tab_find:
        render_directory(filtered_df, location_input)
        st.divider()
        with st.expander("🗺️ Show map (optional)", expanded=False):
            render_map(filtered_df, location_input)

    with tab_about:
        render_analytics(filtered_df)

    st.divider()
    st.caption(
        "Youth Haven does not create accounts or save your searches. "
        "If you are in immediate danger, call 911. For confidential crisis support, "
        "call or text 988."
    )


if __name__ == "__main__":
    main()
