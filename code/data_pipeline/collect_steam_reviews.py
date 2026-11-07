"""Collect up to 500 distinct Steam reviews for each of 20 games.

Run from code/: python -m data_pipeline.collect_steam_reviews
Requires Python 3.8+ and no third-party packages.
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from paths import KNOWLEDGE_BASE_DIR


REVIEWS_PER_GAME = 500
PAGE_SIZE = 100
REVIEWS_ENDPOINT = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
REQUEST_SETTINGS = {
    "language": "english",
    "filter": "all",
    "day_range": 365,
    "review_type": "all",
    "purchase_type": "all",
    "filter_offtopic_activity": 1,
}
GAMES = (
    (1030300, "Hollow Knight: Silksong"),
    (3764200, "Resident Evil Requiem"),
    (1903340, "Clair Obscur: Expedition 33"),
    (2246340, "Monster Hunter Wilds"),
    (1145350, "Hades II"),
    (1091500, "Cyberpunk 2077"),
    (271590, "Grand Theft Auto V Legacy"),
    (1174180, "Red Dead Redemption 2"),
    (367520, "Hollow Knight"),
    (550, "Left 4 Dead 2"),
    (390340, "Umbrella Corps"),
    (1962663, "Call of Duty: Warzone"),
    (1249970, "Test Drive Unlimited Solar Crown"),
    (1294810, "Redfall"),
    (952070, "Resident Evil Resistance"),
    (246090, "Spacebase DF-9"),
    (282560, "RollerCoaster Tycoon World"),
    (1272080, "PAYDAY 3"),
    (1056960, "Wolfenstein: Youngblood"),
    (285190, "Warhammer 40,000: Dawn of War III"),
)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def utc_date(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat() if timestamp is not None else None


def write_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def request_page(url):
    request = Request(url, headers={"User-Agent": "SteamReviewKBResearch/1.0"})
    for attempt in range(4):
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.load(response)
            page = payload.get("response") if isinstance(payload, dict) else None
            if not isinstance(page, dict) or not isinstance(page.get("reviews"), list):
                raise ValueError("Steam returned an unsuccessful or malformed response")
            return payload
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
            retry_after = error.headers.get("Retry-After", "")
            wait = int(retry_after) if retry_after.isdigit() else 2 ** (attempt + 1)
            if wait > 60:
                raise RuntimeError(f"Steam requested a retry after {wait} seconds") from error
        except (URLError, TimeoutError, ConnectionError, ValueError):
            if attempt == 3:
                raise
            wait = 2 ** (attempt + 1)
        print(f"  Temporary request failure; retrying in {wait}s.", flush=True)
        time.sleep(wait)


def normalize(review, appid, game_name):
    author = review.get("author", {})
    steam_id = author.get("steamid")
    return {
        "review_id": str(review["recommendationid"]),
        "appid": appid,
        "game_name": game_name,
        "review_text": review.get("review", ""),
        "language": review.get("language"),
        "steam_recommended": review.get("voted_up"),
        "created_at_utc": utc_date(review.get("timestamp_created")),
        "updated_at_utc": utc_date(review.get("timestamp_updated")),
        "playtime_at_review_minutes": author.get("playtime_at_review"),
        "helpful_votes": review.get("votes_up", 0),
        "weighted_vote_score": review.get("weighted_vote_score"),
        "funny_votes": review.get("votes_funny", 0),
        "steam_purchase": review.get("steam_purchase"),
        "received_for_free": review.get("received_for_free"),
        "written_during_early_access": review.get("written_during_early_access"),
        "source_url": f"https://steamcommunity.com/profiles/{steam_id}/recommended/{appid}/" if steam_id else "",
    }


def collect_game(appid, game_name):
    reviews, pages = [], []
    seen_ids, seen_cursors = set(), set()
    cursor = "*"
    stop_reason, error_message = "page_limit", None

    for _ in range(REVIEWS_PER_GAME + 10):
        if not cursor:
            stop_reason = "missing_cursor"
            break
        if cursor in seen_cursors:
            stop_reason = "repeated_cursor"
            break
        seen_cursors.add(cursor)
        # GetAppReviews uses numeric enums for the legacy filters.
        params = {
            "appid": appid, "languages": [REQUEST_SETTINGS["language"]],
            "filter": 0, "day_range": REQUEST_SETTINGS["day_range"],
            "review_type": 0, "purchase_type": 1, "filter_offtopic_activity": True,
            "num_per_page": PAGE_SIZE, "cursor": cursor,
        }
        query = urlencode({"input_json": json.dumps(params, separators=(",", ":"))})
        url = f"{REVIEWS_ENDPOINT}?{query}"
        try:
            payload = request_page(url)
        except (OSError, RuntimeError, ValueError) as error:
            stop_reason, error_message = "request_failed", str(error)
            break
        page = payload["response"]
        pages.append({"fetched_at_utc": utc_now(), "request_url": url, "response": payload})
        if not page["reviews"]:
            stop_reason = "no_more_reviews"
            break

        for raw in page["reviews"]:
            review_id = raw.get("recommendationid")
            if review_id is None or str(review_id) in seen_ids:
                continue
            seen_ids.add(str(review_id))
            reviews.append(normalize(raw, appid, game_name))
            if len(reviews) == REVIEWS_PER_GAME:
                break
        print(f"  {len(reviews)}/{REVIEWS_PER_GAME} unique reviews", flush=True)
        if len(reviews) == REVIEWS_PER_GAME:
            stop_reason = "target_reached"
            break
        cursor = page.get("cursor")
        time.sleep(1.5)

    return reviews, pages, stop_reason, error_message


def main():
    default_output = KNOWLEDGE_BASE_DIR.with_name("knowledge_base_all_365_500")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=default_output, help="New folder for the collected data")
    output = parser.parse_args().output.resolve()
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f"Output already exists: {output}. Choose a new folder with --output.")

    parameters = {"count_per_game": REVIEWS_PER_GAME, "num_per_page": PAGE_SIZE, **REQUEST_SETTINGS}
    manifest = {
        "created_at_utc": utc_now(),
        "parameters": parameters,
        "catalog_snapshot": [{"appid": appid, "name": name} for appid, name in GAMES],
        "games": [],
        "total_collected_count": 0,
    }
    all_reviews = []

    for index, (appid, name) in enumerate(GAMES, 1):
        if index > 1:
            time.sleep(2)
        print(f"[{index}/{len(GAMES)}] {name}", flush=True)
        started_at = utc_now()
        reviews, pages, reason, error = collect_game(appid, name)
        dates = [review["created_at_utc"] for review in reviews if review["created_at_utc"]]
        metadata = {
            **REQUEST_SETTINGS,
            "appid": appid,
            "game_name": name,
            "requested_count": REVIEWS_PER_GAME,
            "collected_count": len(reviews),
            "started_at_utc": started_at,
            "finished_at_utc": utc_now(),
            "endpoint": REVIEWS_ENDPOINT,
            "oldest_review_created_at_utc": min(dates, default=None),
            "newest_review_created_at_utc": max(dates, default=None),
            "page_count": len(pages),
            "stop_reason": reason,
        }
        if error:
            metadata["error"] = error
        folder = output / f"{appid}_english_all_{REVIEWS_PER_GAME}"
        folder.mkdir()
        write_json(folder / "raw_responses.json", {"metadata": metadata, "pages": pages})
        write_json(folder / "reviews.json", {"metadata": metadata, "reviews": reviews})

        status = "complete" if len(reviews) == REVIEWS_PER_GAME else "partial"
        manifest["games"].append({
            **metadata, "name": name, "folder": folder.name, "count": len(reviews), "status": status,
            "steam_recommended_count": sum(review["steam_recommended"] is True for review in reviews),
            "steam_not_recommended_count": sum(review["steam_recommended"] is False for review in reviews),
        })
        all_reviews.extend(reviews)
        manifest["total_collected_count"] = len(all_reviews)
        write_json(output / "collection_manifest.json", manifest)
        write_json(output / "all_reviews.json", {
            "metadata": {"parameters": parameters, "total_collected_count": len(all_reviews),
                         "manifest": "collection_manifest.json"},
            "reviews": all_reviews,
        })
        print(f"  Saved {len(reviews)} reviews ({reason}).", flush=True)

    complete = sum(game["status"] == "complete" for game in manifest["games"])
    print(f"Saved {len(all_reviews)} reviews to {output}")
    print(f"Games that reached {REVIEWS_PER_GAME} reviews: {complete}/{len(GAMES)}")
    return 0 if complete == len(GAMES) else 2


if __name__ == "__main__":
    raise SystemExit(main())
