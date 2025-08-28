import os
import subprocess
import streamlit as st
import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import uuid
import re

st.set_page_config(page_title="Google Maps Contributor Scraper", layout="wide")
st.title("🔎 Analyseur Google Maps Contributor (réel)")

# ​ Auto-installation de Chromium sur Streamlit Cloud
if not os.path.exists(os.path.expanduser("~/.cache/ms-playwright/chromium")):
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"Erreur installation Chromium : {e}")

url = st.text_input("Collez un lien Google Maps contributor reviews :")

async def scrape_contributor(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)

        await page.wait_for_selector("body", timeout=15000)

        # 1. Nom du contributeur (par sélecteur flexible)
        name = None
        for sel in ["h1", "h2", "span[role='heading']"]:
            try:
                name = (await page.locator(sel).first.text_content()) or None
                if name:
                    break
            except:
                continue

        # 2. Miniature (profil)
        thumbnail = None
        try:
            thumbnail = await page.locator("header img").first.get_attribute("src")
        except:
            pass

        # 3. Texte entier de l’en-tête pour parser les stats
        header_text = ""
        try:
            header_text = await page.locator("header").inner_text()
        except:
            pass

        contributor = {
            "name": name.strip() if name else None,
            "thumbnail": thumbnail,
            "points": None,
            "level": None,
            "local_guide": "Local Guide" in header_text,
            "contributions": {}
        }

        # Extraction de points et niveau s’ils sont présents
        for label in ["points", "pt", "niveau", "level"]:
            match = re.search(r"(\d+)\s*" + re.escape(label), header_text, re.IGNORECASE)
            if match:
                key = "points" if "point" in label else "level"
                contributor[key] = int(match.group(1))

        # Tentative d’extraction de contributions diverses
        for part in header_text.split("\n"):
            m = re.match(r"(\d+)\s+(.+)", part.strip())
            if m:
                contributor["contributions"][m.group(2).lower()] = int(m.group(1))

        # 4. Scroll pour charger les avis
        for _ in range(5):
            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(1000)

        reviews = []
        cards = page.locator("div[data-review-id]")
        count = await cards.count()
        for i in range(count):
            card = cards.nth(i)
            review_id = await card.get_attribute("data-review-id")
            snippet = (await card.text_content()) or ""
            rating = None
            try:
                star = await card.locator("span[role='img']").first.get_attribute("aria-label")
                if star and "étoile" in star:
                    rating = int(re.search(r"(\d)", star).group(1))
            except:
                pass

            reviews.append({
                "review_id": review_id,
                "snippet": snippet.strip(),
                "rating": rating
            })

        await browser.close()
        return contributor, reviews

if url:
    with st.spinner("Extraction en cours..."):
        try:
            contributor, reviews = asyncio.run(scrape_contributor(url))

            search_id = uuid.uuid4().hex[:24]
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            response = {
                "search_metadata": {
                    "id": search_id,
                    "status": "Success",
                    "created_at": timestamp,
                    "processed_at": timestamp,
                    "url": url
                },
                "contributor": contributor,
                "reviews": reviews
            }

            st.json(response)
        except Exception as e:
            st.error(f"Erreur durante scraping : {e}")
