from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlencode
from urllib.request import urlopen

RESULTS_DIR = Path("results")
MAX_ATTEMPTS = 3
WAIT_SECONDS = 30


def as_int(value, default=0):
    if value is None or value == "":
        return default
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default


def require_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


def serpapi_request(api_key, scholar_id, start=0):
    query = urlencode(
        {
            "engine": "google_scholar_author",
            "author_id": scholar_id,
            "hl": "en",
            "num": 100,
            "start": start,
            "api_key": api_key,
        }
    )
    with urlopen(f"https://serpapi.com/search.json?{query}", timeout=60) as response:
        payload = json.load(response)

    if payload.get("error"):
        raise RuntimeError(f"SerpApi error: {payload['error']}")
    if payload.get("search_metadata", {}).get("status") != "Success":
        raise RuntimeError("SerpApi did not return a successful Scholar response")
    return payload


def metric_values(cited_by, metric_name):
    for row in cited_by.get("table", []):
        values = row.get(metric_name)
        if values:
            all_time = as_int(values.get("all"))
            recent = next(
                (
                    as_int(value, all_time)
                    for key, value in values.items()
                    if key != "all" and value is not None
                ),
                all_time,
            )
            return all_time, recent
    return 0, 0


def publication_from_serpapi(article):
    citation_id = article["citation_id"]
    cited_by = article.get("cited_by", {})
    cites_ids = [
        item for item in str(cited_by.get("cites_id", "")).split(",") if item
    ]
    publication = {
        "container_type": "Publication",
        "source": "SERPAPI_AUTHOR_PROFILE",
        "bib": {
            "title": article.get("title", ""),
            "pub_year": str(article.get("year") or ""),
            "citation": article.get("publication") or "",
        },
        "filled": False,
        "author_pub_id": citation_id,
        "num_citations": as_int(cited_by.get("value")),
    }
    if cited_by.get("link"):
        publication["citedby_url"] = cited_by["link"]
    if cites_ids:
        publication["cites_id"] = cites_ids
    return publication


def fetch_with_serpapi(api_key, scholar_id):
    articles = []
    first_payload = None
    start = 0

    while True:
        payload = serpapi_request(api_key, scholar_id, start)
        if first_payload is None:
            first_payload = payload
        page_articles = payload.get("articles", [])
        articles.extend(page_articles)
        if len(page_articles) < 100:
            break
        start += len(page_articles)

    profile = first_payload.get("author", {})
    cited_by = first_payload.get("cited_by", {})
    citations, citations_recent = metric_values(cited_by, "citations")
    h_index, h_index_recent = metric_values(cited_by, "h_index")
    i10_index, i10_index_recent = metric_values(cited_by, "i10_index")
    publications = {
        article["citation_id"]: publication_from_serpapi(article)
        for article in articles
        if article.get("citation_id")
    }

    if not profile.get("name") or not publications:
        raise RuntimeError("SerpApi response is missing the author or publications")

    return {
        "container_type": "Author",
        "filled": ["basics", "publications", "indices", "counts"],
        "scholar_id": scholar_id,
        "source": "SERPAPI_AUTHOR_PROFILE",
        "name": profile["name"],
        "url_picture": profile.get("thumbnail", ""),
        "affiliation": profile.get("affiliations", ""),
        "interests": [item.get("title", "") for item in profile.get("interests", [])],
        "email_domain": profile.get("email", ""),
        "citedby": citations,
        "publications": publications,
        "citedby5y": citations_recent,
        "hindex": h_index,
        "hindex5y": h_index_recent,
        "i10index": i10_index,
        "i10index5y": i10_index_recent,
        "cites_per_year": {
            str(item["year"]): as_int(item.get("citations"))
            for item in cited_by.get("graph", [])
            if item.get("year") is not None
        },
    }


def fetch_with_scholarly(scholar_id):
    from scholarly import ProxyGenerator, scholarly

    errors = []
    connection_modes = ("direct", "free proxy")

    for mode in connection_modes:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                print(f"scholarly {mode}, attempt {attempt}/{MAX_ATTEMPTS}")
                proxy = ProxyGenerator()
                if mode == "free proxy":
                    if not proxy.FreeProxies():
                        raise RuntimeError("No working free proxy was found")
                    scholarly.use_proxy(proxy)
                else:
                    scholarly.use_proxy(proxy, proxy)

                author = scholarly.search_author_id(scholar_id)
                author = scholarly.fill(
                    author,
                    sections=["basics", "indices", "counts", "publications"],
                )
                author["publications"] = {
                    publication["author_pub_id"]: publication
                    for publication in author["publications"]
                }
                return author
            except Exception as exc:
                errors.append(f"{mode} attempt {attempt}: {exc}")
                print(errors[-1], file=sys.stderr)
                if attempt < MAX_ATTEMPTS:
                    time.sleep(WAIT_SECONDS)

    raise RuntimeError("; ".join(errors))


def write_results(author):
    author["updated"] = datetime.now(timezone.utc).isoformat()
    RESULTS_DIR.mkdir(exist_ok=True)
    with (RESULTS_DIR / "gs_data.json").open("w", encoding="utf-8") as outfile:
        json.dump(author, outfile, ensure_ascii=False)

    shield_data = {
        "schemaVersion": 1,
        "label": "citations",
        "message": str(author["citedby"]),
    }
    with (RESULTS_DIR / "gs_data_shieldsio.json").open(
        "w", encoding="utf-8"
    ) as outfile:
        json.dump(shield_data, outfile, ensure_ascii=False)


def main():
    scholar_id = require_env("GOOGLE_SCHOLAR_ID").split("&", 1)[0]
    serpapi_key = os.environ.get("SERPAPI_KEY", "").strip()

    if serpapi_key:
        print("Fetching Google Scholar data through SerpApi")
        try:
            author = fetch_with_serpapi(serpapi_key, scholar_id)
        except Exception as exc:
            print(
                f"SerpApi failed ({exc}); trying the scholarly fallback",
                file=sys.stderr,
            )
            author = fetch_with_scholarly(scholar_id)
    else:
        print(
            "SERPAPI_KEY is not configured; using the less reliable scholarly fallback",
            file=sys.stderr,
        )
        author = fetch_with_scholarly(scholar_id)

    write_results(author)
    print(
        f"Updated {len(author['publications'])} publications; "
        f"total citations: {author['citedby']}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Google Scholar update failed: {exc}", file=sys.stderr)
        sys.exit(1)
