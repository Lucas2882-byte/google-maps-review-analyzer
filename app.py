import os
import subprocess
import streamlit as st
import asyncio
from playwright.async_api import async_playwright
import re

# 🚀 Auto-install Chromium (Streamlit Cloud)
if not os.path.exists(os.path.expanduser("~/.cache/ms-playwright/chromium")):
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"Erreur installation Chromium : {e}")

st.set_page_config(page_title="Google Maps Contributor Analyzer", layout="wide")

# ---- STYLES DARK MODE ----
st.markdown(
    """
    <style>
    body { background-color: #0e1117; color: #fafafa; }
    .profile-card {
        padding: 25px; border-radius: 15px;
        background: linear-gradient(135deg, #1f1c2c, #928dab);
        color: white; margin-bottom: 25px; text-align: center;
    }
    .profile-card h2 { font-size: 1.8em; margin-bottom: 5px; }
    .contrib-card {
        background: #1a1d29; border-radius: 12px; padding: 15px;
        text-align: center; color: #fafafa; margin: 10px;
        box-shadow: 0 3px 8px rgba(0,0,0,0.4);
    }
    .contrib-value { font-size: 1.5em; font-weight: bold; color: #61dafb; }
    .review-card {
        border-radius: 12px; padding: 18px; margin-bottom: 18px;
        background: #1c1f2b; color: #ddd; box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    .review-stars { color: #FFD700; font-size: 1.2em; margin-bottom: 6px; }
    .review-title { font-weight: bold; font-size: 1.1em; margin-bottom: 4px; }
    .review-date { font-size: 0.9em; color: #aaa; margin-bottom: 8px; }
    </style>
    """, unsafe_allow_html=True
)

st.title("🌌 Google Maps Contributor Analyzer")

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

        # Contributions (avis, photos, réponses)
        for line in header_text.split("\n"):
            m = re.match(r"(\d+)\s+([A-Za-zéû]+)", line.strip())
            if m:
                k = m.group(2).lower()
                if k in ["avis", "photos", "réponses"]:
                    contributor["contributions"][k] = int(m.group(1))

        # ---- Charger 100% des avis ----
        reviews = {}
        last_count = -1
        same_count_rounds = 0
        while True:
            count = await page.locator("div[data-review-id]").count()
            if count == last_count:
                same_count_rounds += 1
            else:
                same_count_rounds = 0
            if same_count_rounds >= 3:  # si 3 tours sans nouvel avis, stop
                break
            last_count = count
            await page.mouse.wheel(0, 3000)
            await page.wait_for_timeout(1500)

        cards = page.locator("div[data-review-id]")
        total = await cards.count()
        for i in range(total):
            card = cards.nth(i)
            review_id = await card.get_attribute("data-review-id")
            if not review_id or review_id in reviews:
                continue

            # Nom + adresse
            title = None
            address = None
            try:
                place_block = await card.locator("div[role='link']").first.text_content()
                if place_block:
                    parts = place_block.split("\n")
                    title = parts[0]
                    if len(parts) > 1:
                        address = parts[1]
            except:
                pass

            # Date relative
            date = None
            try:
                spans = await card.locator("span").all_text_contents()
                for s in spans:
                    if "il y a" in s or "ago" in s:
                        date = s
                        break
            except:
                pass

            # Texte
            snippet = (await card.text_content()) or ""
            clean_snippet = snippet.split("Translated by Google")[0]
            clean_snippet = re.sub(r"Visited.*", "", clean_snippet).strip()

            # Note
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
                "title": title.strip() if title else "Lieu inconnu",
                "address": address.strip() if address else "",
                "date": date.strip() if date else "",
                "snippet": clean_snippet,
                "rating": rating
            }

        await browser.close()
        return contributor, list(reviews.values())

# ---- RUN ----
if url:
    with st.spinner("⏳ Extraction en cours... (peut durer quelques secondes)"):
        try:
            contributor, reviews = asyncio.run(scrape_contributor(url))

            # ---- UI PROFILE ----
            st.markdown('<div class="profile-card">', unsafe_allow_html=True)
            st.markdown(f"<h2>{contributor['name']}</h2>", unsafe_allow_html=True)
            if contributor.get("level"):
                st.markdown(f"<p>🎖️ Local Guide Niveau {contributor['level']}</p>", unsafe_allow_html=True)
            if contributor.get("points"):
                st.markdown(f"<p>🏆 {contributor['points']} points</p>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # ---- UI CONTRIBUTIONS ----
            if contributor["contributions"]:
                st.subheader("📊 Contributions")
                cols = st.columns(len(contributor["contributions"]))
                icons = {"avis": "📝", "photos": "📷", "réponses": "💬"}
                for i, (k, v) in enumerate(contributor["contributions"].items()):
                    with cols[i]:
                        st.markdown('<div class="contrib-card">', unsafe_allow_html=True)
                        st.markdown(f"<div class='contrib-value'>{icons.get(k, '📊')} {v}</div>", unsafe_allow_html=True)
                        st.markdown(f"<p>{k.capitalize()}</p>", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

            # ---- UI REVIEWS ----
            st.subheader("📝 Avis publiés")
            for r in reviews:
                stars = "⭐" * int(r["rating"]) if r["rating"] else "❓"
                st.markdown(f"""
                    <div class="review-card">
                        <div class="review-title">📍 {r["title"]}</div>
                        <div class="review-date">⏳ {r["date"]}</div>
                        <div class="review-stars">{stars}</div>
                        <div class="review-date">🏠 {r["address"]}</div>
                        <p>💬 {r["snippet"]}</p>
                    </div>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erreur scraping : {e}")
