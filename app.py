import os
import subprocess
import streamlit as st
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import uuid
import re

# 🚀 Auto-install Chromium pour Streamlit Cloud
if not os.path.exists(os.path.expanduser("~/.cache/ms-playwright/chromium")):
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"Erreur installation Chromium : {e}")

# ---- CONFIG ----
st.set_page_config(page_title="Google Maps Contributor Analyzer", layout="wide")

# ---- DARK MODE STYLE ----
st.markdown(
    """
    <style>
    body {
        background-color: #0e1117;
        color: #fafafa;
    }
    .title {
        font-size: 2.2em;
        font-weight: bold;
        color: #61dafb;
        text-align: center;
        margin-bottom: 30px;
    }
    .profile-card {
        padding: 25px;
        border-radius: 15px;
        background: linear-gradient(135deg, #1f1c2c, #928dab);
        color: white;
        margin-bottom: 25px;
        text-align: center;
    }
    .profile-card h2 {
        font-size: 1.8em;
        margin-bottom: 5px;
    }
    .badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 30px;
        background: #61dafb;
        color: black;
        font-weight: bold;
        font-size: 0.9em;
        margin: 5px;
    }
    .contrib-card {
        background: #1a1d29;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        color: #fafafa;
        margin: 10px;
        box-shadow: 0 3px 8px rgba(0,0,0,0.4);
    }
    .contrib-value {
        font-size: 1.5em;
        font-weight: bold;
        color: #61dafb;
    }
    .review-card {
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 18px;
        background: #1c1f2b;
        color: #ddd;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    .review-stars {
        color: #FFD700;
        font-size: 1.2em;
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="title">🌌 Google Maps Contributor Analyzer</div>', unsafe_allow_html=True)

url = st.text_input("🔗 Collez un lien Google Maps contributor reviews :")

# ---- SCRAPER ----
async def scrape_contributor(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        await page.wait_for_selector("body", timeout=15000)

        # Nom
        name = None
        for sel in ["h1", "h2", "span[role='heading']"]:
            try:
                name = (await page.locator(sel).first.text_content()) or None
                if name:
                    break
            except:
                continue

        header_text = await page.locator("body").inner_text()

        contributor = {
            "name": name.strip() if name else "Inconnu",
            "points": None,
            "level": None,
            "local_guide": "Local Guide" in header_text,
            "contributions": {}
        }

        # Points & Level
        match_pts = re.search(r"(\d+)\s*points", header_text, re.IGNORECASE)
        if match_pts: contributor["points"] = int(match_pts.group(1))

        match_lvl = re.search(r"Niveau\s+(\d+)", header_text, re.IGNORECASE)
        if match_lvl: contributor["level"] = int(match_lvl.group(1))

        # Contributions diverses
        for line in header_text.split("\n"):
            m = re.match(r"(\d+)\s+([A-Za-zéû]+)", line.strip())
            if m:
                contributor["contributions"][m.group(2).lower()] = int(m.group(1))

        # Avis
        for _ in range(5):
            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(1000)

        reviews = {}
        cards = page.locator("div[data-review-id]")
        count = await cards.count()
        for i in range(count):
            card = cards.nth(i)
            review_id = await card.get_attribute("data-review-id")
            if not review_id or review_id in reviews:
                continue
            snippet = (await card.text_content()) or ""
            rating = None
            try:
                star = await card.locator("span[role='img']").first.get_attribute("aria-label")
                if star:
                    m = re.search(r"([0-9](?:[.,][0-9])?)", star)
                    if m:
                        rating = float(m.group(1).replace(",", "."))
            except:
                pass

            reviews[review_id] = {
                "review_id": review_id,
                "snippet": snippet.strip(),
                "rating": rating
            }

        await browser.close()
        return contributor, list(reviews.values())

# ---- RUN ----
if url:
    with st.spinner("⏳ Extraction en cours..."):
        try:
            contributor, reviews = asyncio.run(scrape_contributor(url))

            # ---- UI PROFILE ----
            st.markdown('<div class="profile-card">', unsafe_allow_html=True)
            st.markdown(f"<h2>{contributor['name']}</h2>", unsafe_allow_html=True)
            st.markdown(
                f"<p>⭐ Niveau {contributor.get('level') or '?'} | {contributor.get('points') or '?'} points</p>",
                unsafe_allow_html=True
            )
            if contributor["local_guide"]:
                st.markdown('<span class="badge">🌍 Local Guide</span>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # ---- UI CONTRIBUTIONS ----
            if contributor["contributions"]:
                st.subheader("📊 Contributions")
                cols = st.columns(len(contributor["contributions"]))
                for i, (k, v) in enumerate(contributor["contributions"].items()):
                    with cols[i]:
                        st.markdown('<div class="contrib-card">', unsafe_allow_html=True)
                        st.markdown(f"<div class='contrib-value'>{v}</div>", unsafe_allow_html=True)
                        st.markdown(f"<p>{k.capitalize()}</p>", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

            # ---- UI REVIEWS ----
            st.subheader("📝 Avis publiés")
            for r in reviews:
                stars = "⭐" * int(r["rating"]) if r["rating"] else "❓"
                st.markdown(f"""
                    <div class="review-card">
                        <div class="review-stars">{stars}</div>
                        <p>{r["snippet"][:800]}...</p>
                    </div>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erreur scraping : {e}")
