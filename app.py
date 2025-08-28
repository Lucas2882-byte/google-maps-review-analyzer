import streamlit as st
import asyncio
from playwright.async_api import async_playwright
import re
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import uuid

st.set_page_config(page_title="Google Maps Contributor Scraper", layout="wide")
st.title("🔎 Analyseur Google Maps Contributor")

url = st.text_input("Collez un lien Google Maps contributor reviews :")

async def scrape_contributor(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)

        # Attente que le profil charge
        await page.wait_for_selector("div[role='main']", timeout=15000)

        # Récupération infos contributeur
        name = await page.locator("div[data-attribution-id] span").first.text_content()
        thumbnail = await page.locator("img[alt*='Photo de profil'], img[alt*='Profile']").first.get_attribute("src")
        stats = await page.locator("div[data-testid='contribution-stat']").all_text_contents()

        contributor_info = {
            "name": name.strip() if name else "Inconnu",
            "thumbnail": thumbnail,
            "points": None,
            "level": None,
            "local_guide": "Local Guide" in " ".join(stats),
            "contributions": {}
        }

        # Essai d’extraire points & niveau
        for s in stats:
            if "points" in s.lower():
                contributor_info["points"] = int(re.sub(r"[^0-9]", "", s))
            if "niveau" in s.lower() or "level" in s.lower():
                contributor_info["level"] = int(re.sub(r"[^0-9]", "", s))

        # Contributions (avis, photos…)
        for s in stats:
            parts = s.split("·")
            for part in parts:
                kv = part.strip().split(" ")
                if len(kv) == 2:
                    k, v = kv
                    contributor_info["contributions"][v.lower()] = int(re.sub(r"[^0-9]", "", k))

        # Scroll pour charger les avis
        reviews = []
        review_cards = page.locator("div[data-review-id]")
        count = await review_cards.count()
        for i in range(count):
            r = review_cards.nth(i)
            review_id = await r.get_attribute("data-review-id")
            snippet = await r.text_content()
            place = await r.locator("div[role='link']").first.text_content()
            rating_el = await r.locator("span[role='img']").first.get_attribute("aria-label")
            rating = None
            if rating_el and "étoile" in rating_el:
                rating = int(re.search(r"([0-9])", rating_el).group(1))
            reviews.append({
                "review_id": review_id,
                "place": place.strip() if place else None,
                "snippet": snippet.strip() if snippet else None,
                "rating": rating
            })

        await browser.close()

        return contributor_info, reviews


if url:
    try:
        contributor_info, reviews = asyncio.run(scrape_contributor(url))

        search_id = uuid.uuid4().hex[:24]
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        response = {
            "search_metadata": {
                "id": search_id,
                "status": "Success",
                "created_at": timestamp,
                "processed_at": timestamp,
                "google_maps_contributor_reviews_url": url,
            },
            "contributor": contributor_info,
            "reviews": reviews
        }

        st.json(response)

    except Exception as e:
        st.error(f"Erreur : {e}")
