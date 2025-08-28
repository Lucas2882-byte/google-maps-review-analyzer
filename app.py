import streamlit as st
from urllib.parse import urlparse, parse_qs
import re
import uuid
import time
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Google Maps Review Analyzer", layout="wide")

st.title("🔎 Analyseur de lien Google Maps Contributor Reviews")

url = st.text_input("Collez un lien Google Maps contributor reviews :")

if url:
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # Extraction contributor_id
    user_id_match = re.search(r"contrib/(\d+)/reviews", parsed.path)
    contributor_id = user_id_match.group(1) if user_id_match else None

    # Langues par défaut
    hl = query_params.get("hl", ["fr"])[0]
    gl = query_params.get("gl", ["fr"])[0]

    # Métadonnées factices
    search_id = uuid.uuid4().hex[:24]
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # Réponse JSON mockée (à enrichir plus tard avec scraping si besoin)
    response = {
        "search_metadata": {
            "id": search_id,
            "status": "Success",
            "json_endpoint": f"https://api.example.com/searches/{search_id}.json",
            "created_at": timestamp,
            "processed_at": timestamp,
            "google_maps_contributor_reviews_url": f"https://www.google.com/maps/contrib/{contributor_id}/reviews?gl={gl}&hl={hl}",
            "raw_html_file": f"https://api.example.com/searches/{search_id}.html",
            "prettify_html_file": f"https://api.example.com/searches/{search_id}.prettify",
            "total_time_taken": round(time.perf_counter(), 2)
        },
        "search_parameters": {
            "engine": "google_maps_contributor_reviews",
            "gl": gl,
            "hl": hl,
            "contributor_id": contributor_id
        },
        "contributor": {
            "name": "Mock User",
            "thumbnail": "https://via.placeholder.com/120",
            "points": 77,
            "level": 3,
            "local_guide": True,
            "contributions": {
                "avis": 2,
                "photos": 0,
                "vidéos": 0
            }
        },
        "reviews": [
            {
                "place_info": {
                    "title": "Entreprise Exemple",
                    "address": "123 Rue Fictive, Paris",
                    "gps_coordinates": {
                        "latitude": 48.8566,
                        "longitude": 2.3522
                    },
                    "type": "Restaurant",
                    "thumbnail": "https://via.placeholder.com/200",
                    "data_id": "0x123456789abcdef"
                },
                "date": "il y a 2 mois",
                "snippet": "Super expérience, je recommande !",
                "review_id": "mock_review_1",
                "rating": 5,
                "likes": 2,
                "link": "https://www.google.com/maps/reviews/data=mock1",
                "response": {
                    "date": "il y a 2 mois",
                    "snippet": "Merci pour votre avis positif !"
                }
            }
        ]
    }

    st.subheader("Résultat JSON")
    st.json(response)

st.markdown("---")
st.caption("⚡ Version démo mockée. Peut être étendue avec du scraping pour avoir de vraies données.")
