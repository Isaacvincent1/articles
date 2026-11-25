import json
import os
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

PAGE_URL = "https://www.leftcom.org/fr/recent_articles"
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
SEEN_FILE = "seen.json"
MAX_POSTS = 5 

ARTICLE_RE = re.compile(r"/fr/articles/\d{4}-\d{2}-\d{2}/")


def fetch_articles():
    """Retourne {url: titre}, du plus récent au plus ancien (ordre de la page)."""
    r = requests.get(
        PAGE_URL,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (discord-article-notifier)"},
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    articles = {}
    for a in soup.find_all("a", href=True):
        url = urljoin(PAGE_URL, a["href"]).split("#")[0]
        if not ARTICLE_RE.search(url):
            continue
        title = " ".join(a.get_text().split())
        # Un même article a plusieurs liens (image, titre, "mostra") :
        # on garde le texte le plus long, c'est le titre.
        if url not in articles or len(title) > len(articles[url]):
            articles[url] = title
    return articles


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return None  


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, indent=2)


def post_to_discord(title, url):
    r = requests.post(
        WEBHOOK_URL,
        json={"content": f"📰 **Nouvel article** \n{url}"},
        timeout=30,
    )
    r.raise_for_status()


def main():
    articles = fetch_articles()
    if not articles:
        sys.exit("Aucun article trouvé : la page a peut-être changé de structure.")

    seen = load_seen()

    # Premier lancement : on mémorise l'existant sans rien envoyer.
    if seen is None:
        save_seen(set(articles))
        print(f"Initialisation : {len(articles)} articles mémorisés.")
        return

    new = [(u, t) for u, t in articles.items() if u not in seen]
    to_post = new[:MAX_POSTS]

    # On poste du plus ancien au plus récent.
    for url, title in reversed(to_post):
        post_to_discord(title or "Nouvel article", url)
        seen.add(url)
        save_seen(seen)  # sauvegarde après chaque envoi réussi
        time.sleep(1)

    # Les éventuels articles au-delà de MAX_POSTS sont marqués comme vus.
    seen.update(articles)
    save_seen(seen)
    print(f"{len(to_post)} nouvel(s) article(s) envoyé(s).")


if __name__ == "__main__":
    main()
