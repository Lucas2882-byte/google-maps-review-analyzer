import os
import subprocess
import streamlit as st
import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse
from datetime import datetime
import uuid
import re

# 🚀 Auto-install Chromium (Streamlit Cloud)
if not os.path.exists(os.path.expanduser("~/.cache/ms-playwright/chromium")):
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"Erreur installation Chromium : {e}")

st.set_page_config(page_title="Google Maps Contributor Analyzer", layout="wide")

# ---- UI HEADER ----
st.markdown(
    """
    <style>
    .profile-card {
        display: flex; 
        align-items: center; 
        gap: 20px; 
        padding: 20px; 
        border-radius: 15px; 
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        margin-bottom: 20px;
    }
    .profile-card img {
        border-radius: 50%;
        width: 100px;
        height: 100px;
        object-fit: cover;
        border: 3px solid white;
    }
    .review-card {
        border: 1px solid #eee;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        background-color: white;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    .stars {
        color: gold;
        font-size: 18px;
    }
    </style>
    """, unsafe_allow_html=True
)

st.title("🔎 Google Maps Contributor Analyzer")

url = st.text_input("Collez un lien Google Maps contributor reviews :")

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

        # Thumbnail
        thumbnail = None
        try:
            thumbnail = await page.locator("header img").first.get_attribute("src")
        except:
            pass

        # Profil complet (bloc de stats)
        header_text = ""
        try:
            header_text = await page.locator("body").inner_text()
        except:
            pass

        contributor = {
            "name": name.strip() if name else "Inconnu",
            "thumbnail": thumbnail,
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

            # Rating
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
            if contributor["thumbnail"]:
                st.markdown(f'<img src="{contributor["thumbnail"]}" alt="photo">', unsafe_allow_html=True)
            else:
                st.markdown(f'<img src="https://via.placeholder.com/100" alt="no photo">', unsafe_allow_html=True)
            st.markdown(f"""
                <div>
                    <h2>{contributor["name"]}</h2>
                    <p>⭐ Niveau {contributor.get("level") or "?"} | {contributor.get("points") or "?"} points</p>
                    <p>{'🌍 Local Guide' if contributor["local_guide"] else ''}</p>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # ---- UI CONTRIBUTIONS ----
            if contributor["contributions"]:
                st.subheader("📊 Contributions")
                cols = st.columns(len(contributor["contributions"]))
                for i, (k, v) in enumerate(contributor["contributions"].items()):
                    cols[i].metric(k.capitalize(), v)

            # ---- UI REVIEWS ----
            st.subheader("📝 Avis publiés")
            for r in reviews:
                stars = "⭐" * int(r["rating"]) if r["rating"] else "❓"
                st.markdown(f"""
                    <div class="review-card">
                        <div class="stars">{stars}</div>
                        <p>{r["snippet"][:500]}...</p>
                    </div>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erreur scraping : {e}")
