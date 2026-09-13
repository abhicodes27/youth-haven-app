"""Youth Haven: Emergency Resource Finder for Displaced Youth."""

import json
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
        if st.button("🚪 Quick Exit", help="Immediately leave this site and clear your session", use_container_width=True, type="primary"):
            quick_exit()

    st.markdown(
        """
        > **You are not alone.** Youth Haven helps young people facing housing
        > instability, sudden displacement, or homelessness find immediate
        > shelter, food, legal aid, and crisis support — instantly, safely,
        > and without tracking, saving, or sharing your personal data.
        > Every search here disappears when you leave.
        """
    )
    st.divider()


def render_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("🔎 Find What You Need")
    st.sidebar.caption("Filters help narrow results. Nothing you select is stored or sent anywhere.")

    categories = sorted(df["category"].dropna().unique().tolist()) if not df.empty else []
    cities = sorted(df["city"].dropna().unique().tolist()) if not df.empty else []
    age_ranges = sorted(df["age_range"].dropna().unique().tolist()) if not df.empty else []

    selected_categories = st.sidebar.multiselect("Category", options=categories, default=categories)
    selected_cities = st.sidebar.multiselect("City", options=cities, default=cities)
    selected_ages = st.sidebar.multiselect("Age Range", options=age_ranges, default=age_ranges)
    walk_in_only = st.sidebar.checkbox("Walk-ins only", value=False)

    st.sidebar.divider()
    st.sidebar.markdown(
        "**In immediate danger?**\n\nCall or text **988** (Suicide & Crisis Lifeline)\n\n"
        "or **911** for emergencies."
    )

    filtered = df.copy()
    if selected_categories:
        filtered = filtered[filtered["category"].isin(selected_categories)]
    if selected_cities:
        filtered = filtered[filtered["city"].isin(selected_cities)]
    if selected_ages:
        filtered = filtered[filtered["age_range"].isin(selected_ages)]
    if walk_in_only:
        filtered = filtered[filtered["walk_in_allowed"]]

    return filtered


def render_map(df: pd.DataFrame):
    st.subheader("📍 Nearby Resources")

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

    st_folium(fmap, width=None, height=480, returned_objects=[])


def render_directory(df: pd.DataFrame):
    st.subheader("📇 Resource Directory")

    if df.empty:
        st.warning("No resources match your current filters.")
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


def render_analytics(df: pd.DataFrame):
    st.subheader("📊 Regional Resource Overview")

    if df.empty:
        st.info("No data available to display analytics.")
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

    filtered_df = render_filters(resources_df)

    tab_find, tab_analytics = st.tabs(["🧭 Find Resources", "📈 Analytics"])

    with tab_find:
        render_map(filtered_df)
        st.divider()
        render_directory(filtered_df)

    with tab_analytics:
        render_analytics(filtered_df)

    st.divider()
    st.caption(
        "Youth Haven does not collect, store, or share any personal data. "
        "If you are in immediate danger, call 911. For confidential crisis support, "
        "call or text 988."
    )


if __name__ == "__main__":
    main()
