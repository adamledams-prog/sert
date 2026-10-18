"""
fetch_brawlers.py
-----------------
Télécharge les images de brawlers Brawl Stars depuis le wiki Fandom.
Les images sont sauvegardées dans le dossier ./images/
"""

import os
import re
import time
import requests

# ── Configuration ─────────────────────────────────────────────────────────────

# Tes brawlers préférés (ajoute ou retire des noms ici)
BRAWLERS = [
    "Shelly",
    "Colt",
    "Bull",
    "Brock",
    "El_Primo",
    "Barley",
    "Poco",
    "Rosa",
    "Jessie",
    "Dynamike",
    "Tick",
    "8-Bit",
    "Rico",
    "Darryl",
    "Penny",
    "Jacky",
    "Gus",
    "Bo",
    "Emz",
    "Stu",
    "Piper",
    "Pam",
    "Frank",
    "Bibi",
    "Bea",
    "Nani",
    "Edgar",
    "Griff",
    "Grom",
    "Bonnie",
    "Gale",
    "Colette",
    "Belle",
    "Ash",
    "Lola",
    "Sam",
    "Mandy",
    "Maisie",
    "Hank",
    "Pearl",
    "Larry_&_Lawrie",
    "Angelo",
    "Berry",
    "Clancy",
    "Moe",
    "Melodie",
    "Lily",
    "Draco",
    "Juju",
    "Finx",
    "Mortis",
    "Tara",
    "Gene",
    "Max",
    "Mr._P",
    "Sprout",
    "Byron",
    "Squeak",
    "Lou",
    "Ruffs",
    "Eve",
    "Janet",
    "Otis",
    "Buster",
    "Gray",
    "Willow",
    "Doug",
    "Chuck",
    "Charlie",
    "Mico",
    "Cordelius",
    "Kit",
    "Amber",
    "Meg",
    "Surge",
    "Chester",
    "Sandy",
    "Spike",
    "Crow",
    "Leon",
    "Buzz",
    "R-T",
    "Fang",
]

OUTPUT_DIR = "images"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
# API MediaWiki publique (pas de blocage 403)
MEDIAWIKI_API = "https://brawlstars.fandom.com/api.php"
DELAY_BETWEEN_REQUESTS = 0.5  # secondes (pour ne pas surcharger le serveur)

# ── Fonctions ─────────────────────────────────────────────────────────────────

def get_default_skin_image(brawler_name: str) -> str | None:
    """
    Utilise l'API MediaWiki de Fandom pour obtenir l'URL de l'image Skin-Default.
    Essaie d'abord le nom exact, puis avec variantes de casse.
    Retourne None si introuvable.
    """
    # Le fichier wiki suit ce pattern : "BrawlerName_Skin-Default.png"
    file_title = f"File:{brawler_name}_Skin-Default.png"

    params = {
        "action": "query",
        "titles": file_title,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
    }

    try:
        resp = requests.get(MEDIAWIKI_API, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"  [ERREUR] API échouée pour {brawler_name} : {e}")
        return None

    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        imageinfo = page.get("imageinfo", [])
        if imageinfo:
            return imageinfo[0].get("url")

    return None


def download_image(image_url: str, dest_path: str) -> bool:
    """Télécharge une image vers dest_path. Retourne True si succès."""
    try:
        resp = requests.get(image_url, headers=HEADERS, timeout=15, stream=True)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except requests.RequestException as e:
        print(f"  [ERREUR] Téléchargement échoué ({image_url}) : {e}")
        return False


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    successes, failures = [], []

    print(f"{'='*55}")
    print(f"  Récupération de {len(BRAWLERS)} brawler(s)")
    print(f"  Dossier de sortie : ./{OUTPUT_DIR}/")
    print(f"{'='*55}\n")

    for brawler in BRAWLERS:
        display_name = brawler.replace("_", " ")
        print(f"[{brawler}]")

        # Détermine le nom de fichier de sortie
        safe_name = re.sub(r"[^\w\-]", "_", brawler)
        dest_path = os.path.join(OUTPUT_DIR, f"{safe_name}.png")

        if os.path.exists(dest_path):
            print(f"  ✓ Déjà téléchargé, on passe.\n")
            successes.append(brawler)
            continue

        image_url = get_default_skin_image(brawler)

        if not image_url:
            print(f"  ✗ Image introuvable sur le wiki.\n")
            failures.append(brawler)
            time.sleep(DELAY_BETWEEN_REQUESTS)
            continue

        print(f"  URL : {image_url}")
        ok = download_image(image_url, dest_path)
        if ok:
            print(f"  ✓ Sauvegardé : {dest_path}\n")
            successes.append(brawler)
        else:
            failures.append(brawler)
            print()

        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Résumé
    print(f"\n{'='*55}")
    print(f"  ✓ Succès : {len(successes)}")
    print(f"  ✗ Échecs : {len(failures)}")
    if failures:
        print(f"\n  Brawlers non récupérés :")
        for name in failures:
            print(f"    - {name}")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
