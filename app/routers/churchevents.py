import logging
import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import Church, ChurchEvent, ChurchLink, ZipLookup, get_db
from app.xai_client import llm_web_search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/churchevents", tags=["churchevents"])


class ChurchesRequest(BaseModel):
    zip_code: str
    force: bool = False


def _normalize_name(name: str) -> str:
    """Lowercase, strip punctuation/whitespace for fuzzy matching."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _merge_churches(
    db: Session,
    zip_code: str,
    found_items: list[dict],
    existing: list[Church],
) -> tuple[list[Church], int]:
    """Merge newly found churches with existing DB rows. Returns (all_churches, new_count)."""
    existing_map: dict[str, Church] = {}
    for c in existing:
        existing_map[_normalize_name(c.name)] = c

    now = datetime.utcnow()
    new_count = 0

    for item in found_items:
        raw_name = item.get("name", "").strip()
        if not raw_name or raw_name.lower() == "unknown":
            continue
        norm = _normalize_name(raw_name)
        if norm in existing_map:
            church = existing_map[norm]
            church.last_seen_at = now
            if item.get("denomination"):
                church.denomination = item["denomination"]
            if item.get("address") and not church.address:
                church.address = item["address"]
        else:
            church = Church(
                zip_code=zip_code,
                name=raw_name,
                denomination=item.get("denomination", ""),
                address=item.get("address", ""),
                discovered_at=now,
                last_seen_at=now,
            )
            db.add(church)
            existing_map[norm] = church
            new_count += 1

    return list(existing_map.values()), new_count


# ---------------------------------------------------------------------------
# Stage 1 – Discover churches for a zip code (web search, multi-pass)
# ---------------------------------------------------------------------------

@router.post("/churches")
async def find_churches(req: ChurchesRequest, db: Session = Depends(get_db)):
    zip_lookup = db.query(ZipLookup).filter_by(zip_code=req.zip_code).first()
    existing = db.query(Church).filter_by(zip_code=req.zip_code).all()

    if zip_lookup and zip_lookup.churches_updated_at and not req.force:
        return {
            "zip_code": req.zip_code,
            "cached": True,
            "churches_updated_at": zip_lookup.churches_updated_at.isoformat(),
            "churches": [_church_dict(c) for c in existing],
        }

    if not zip_lookup:
        zip_lookup = ZipLookup(zip_code=req.zip_code)
        db.add(zip_lookup)
        db.flush()

    example = '{"city":"...","state":"...","churches":[{"name":"...","denomination":"...","address":"..."}]}'

    # Pass 1: broad web search for churches & places of worship
    prompt_1 = (
        f"Search the web for a comprehensive list of ALL churches, places of worship, "
        f"and religious congregations in or near zip code {req.zip_code}. "
        f"Include every denomination: Catholic, Baptist, Methodist, Presbyterian, "
        f"Episcopal, Lutheran, Pentecostal, non-denominational, Jewish synagogues, "
        f"mosques, and any other house of worship. "
        f"Check Google Maps, Yelp, Yellow Pages, and church directories. "
        f"Also provide the city and state for this zip code. "
        f"Return JSON: {example}"
    )

    all_found: list[dict] = []
    city = ""
    state = ""

    try:
        data = await llm_web_search(prompt_1)
        city = data.get("city", "")
        state = data.get("state", "")
        all_found.extend(data.get("churches", []))
    except Exception as e:
        logger.exception("xAI web search failed for Stage 1 pass 1")
        raise HTTPException(status_code=502, detail=f"xAI API error: {e}")

    # Pass 2: ask for anything missed, providing the names already found
    already_names = [c.get("name", "") for c in all_found]
    already_str = ", ".join(already_names) if already_names else "(none found yet)"

    prompt_2 = (
        f"I already found these churches/places of worship in zip code {req.zip_code}: "
        f"{already_str}. "
        f"Search the web again for any churches, congregations, ministries, fellowships, "
        f"chapels, temples, mosques, or synagogues in or near {req.zip_code} that are NOT "
        f"in the list above. Check Google Maps, church directories, Yelp, and local listings. "
        f"Return ONLY the ones not already listed. "
        f'Return JSON: {{"churches":[{{"name":"...","denomination":"...","address":"..."}}]}}'
    )

    try:
        data2 = await llm_web_search(prompt_2)
        all_found.extend(data2.get("churches", []))
    except Exception:
        logger.warning("Stage 1 pass 2 failed; continuing with pass 1 results")

    # Merge found churches with any existing DB records
    all_churches, new_count = _merge_churches(db, req.zip_code, all_found, existing)

    zip_lookup.city = city or zip_lookup.city or ""
    zip_lookup.state = state or zip_lookup.state or ""
    zip_lookup.churches_updated_at = datetime.utcnow()

    db.commit()
    for c in all_churches:
        db.refresh(c)

    return {
        "zip_code": req.zip_code,
        "cached": False,
        "new_churches": new_count,
        "total_churches": len(all_churches),
        "churches_updated_at": zip_lookup.churches_updated_at.isoformat(),
        "churches": [_church_dict(c) for c in all_churches],
    }


@router.get("/zip-codes")
async def list_zip_codes(db: Session = Depends(get_db)):
    lookups = db.query(ZipLookup).filter(ZipLookup.churches_updated_at.isnot(None)).all()
    result = []
    for zl in lookups:
        count = db.query(Church).filter_by(zip_code=zl.zip_code).count()
        result.append({
            "zip_code": zl.zip_code,
            "city": zl.city,
            "state": zl.state,
            "church_count": count,
            "churches_updated_at": zl.churches_updated_at.isoformat() if zl.churches_updated_at else None,
        })
    result.sort(key=lambda x: x["zip_code"])
    return result


@router.get("/churches/{zip_code}")
async def get_churches(zip_code: str, db: Session = Depends(get_db)):
    zip_lookup = db.query(ZipLookup).filter_by(zip_code=zip_code).first()
    churches = db.query(Church).filter_by(zip_code=zip_code).all()
    return {
        "zip_code": zip_code,
        "city": zip_lookup.city if zip_lookup else None,
        "state": zip_lookup.state if zip_lookup else None,
        "churches_updated_at": zip_lookup.churches_updated_at.isoformat() if zip_lookup and zip_lookup.churches_updated_at else None,
        "churches": [_church_dict(c) for c in churches],
    }


# ---------------------------------------------------------------------------
# Stage 2 – Gather links for every church in a zip code
# ---------------------------------------------------------------------------

LINK_STALE_DAYS = 30


@router.post("/links/{zip_code}")
async def gather_links(zip_code: str, db: Session = Depends(get_db)):
    churches = db.query(Church).filter_by(zip_code=zip_code).all()
    if not churches:
        raise HTTPException(status_code=404, detail="No churches found for this zip code. Run Stage 1 first.")

    now = datetime.utcnow()
    stale_cutoff = now - timedelta(days=LINK_STALE_DAYS)
    total_new = 0
    skipped = 0

    for church in churches:
        if church.links_updated_at and church.links_updated_at > stale_cutoff:
            skipped += 1
            continue

        existing_links = db.query(ChurchLink).filter_by(church_id=church.id).all()
        existing_map: dict[str, ChurchLink] = {
            lk.url.rstrip("/").lower(): lk for lk in existing_links
        }

        example = '[{"url": "https://...", "platform": "website"}]'
        prompt = (
            f"Search the web for '{church.name}' located at '{church.address}'. "
            f"Find all online presence: official website, Facebook page, Instagram, "
            f"YouTube, Twitter/X, event pages, community calendars. "
            f"Return a JSON array of objects with 'url' and 'platform' fields. "
            f"Example: {example}. "
            f"If you find nothing, return an empty array []."
        )

        try:
            links_data = await llm_web_search(prompt)
        except Exception:
            logger.exception(f"xAI web search failed for church: {church.name}")
            continue

        if not isinstance(links_data, list):
            links_data = links_data.get("links", []) if isinstance(links_data, dict) else []

        for link_item in links_data:
            url = link_item.get("url", "").strip()
            if not url:
                continue
            norm_url = url.rstrip("/").lower()
            if norm_url in existing_map:
                existing_map[norm_url].last_seen_at = now
            else:
                church_link = ChurchLink(
                    church_id=church.id,
                    url=url,
                    platform=link_item.get("platform", "other"),
                    discovered_at=now,
                    last_seen_at=now,
                )
                db.add(church_link)
                existing_map[norm_url] = church_link
                total_new += 1

        church.links_updated_at = now

    db.commit()

    churches = db.query(Church).filter_by(zip_code=zip_code).all()
    total_links = sum(len(c.links) for c in churches)
    return {
        "zip_code": zip_code,
        "new_links": total_new,
        "skipped_churches": skipped,
        "total_links": total_links,
        "churches": [_church_with_links_dict(c) for c in churches],
    }


# ---------------------------------------------------------------------------
# Stage 3 – Extract events from event-worthy links
# ---------------------------------------------------------------------------

SKIP_PLATFORMS = {
    "instagram", "youtube", "twitter/x", "twitter", "x",
    "linkedin", "pinterest", "threads", "bluesky", "tiktok",
    "yelp", "mapquest", "faithstreet", "linktree",
}

EVENT_STALE_DAYS = 7


def _is_event_worthy(link: ChurchLink) -> bool:
    """Skip social media profiles and directory listings that won't have scrapable events."""
    if link.platform and link.platform.lower() in SKIP_PLATFORMS:
        return False
    url_lower = (link.url or "").lower()
    skip_domains = [
        "instagram.com", "youtube.com", "youtu.be", "twitter.com",
        "x.com", "linkedin.com", "pinterest.com", "threads.net",
        "tiktok.com", "yelp.com", "mapquest.com", "linktree",
    ]
    return not any(d in url_lower for d in skip_domains)


@router.post("/events/{zip_code}")
async def extract_events(zip_code: str, db: Session = Depends(get_db)):
    churches = db.query(Church).filter_by(zip_code=zip_code).all()
    if not churches:
        raise HTTPException(status_code=404, detail="No churches found. Run Stage 1 first.")

    now = datetime.utcnow()
    stale_cutoff = now - timedelta(days=EVENT_STALE_DAYS)

    worthy_links = []
    for church in churches:
        links = db.query(ChurchLink).filter_by(church_id=church.id).all()
        for link in links:
            if not _is_event_worthy(link):
                continue
            if link.events_scraped_at and link.events_scraped_at > stale_cutoff:
                continue
            worthy_links.append(link)

    if not worthy_links:
        existing_events = (
            db.query(ChurchEvent)
            .filter(ChurchEvent.church_id.in_([c.id for c in churches]))
            .count()
        )
        if existing_events:
            return await get_events(zip_code, db)
        raise HTTPException(
            status_code=404,
            detail="No scrapable links found. Run Stage 2 first, or all links were recently scraped.",
        )

    total_events = 0
    for link in worthy_links:
        example = '[{"name": "...", "description": "...", "date": "2025-06-15", "time": "10:00 AM", "location": "...", "image_url": ""}]'
        prompt = (
            f"Visit this URL: {link.url}\n"
            f"Extract all upcoming events, services, or gatherings from this page. "
            f"For each event, provide: name, description, date (ISO format YYYY-MM-DD if possible), "
            f"time, location, and any image URL. "
            f"Return a JSON array of objects. If no events are found, return an empty array [].\n"
            f"Example: {example}"
        )

        try:
            events_data = await llm_web_search(
                prompt,
                system_prompt="You are an event extraction assistant. Return JSON only.",
            )
        except Exception:
            logger.exception(f"xAI event extraction failed for link: {link.url}")
            continue

        if not isinstance(events_data, list):
            events_data = events_data.get("events", []) if isinstance(events_data, dict) else []

        # Remove old events from this specific link before inserting fresh ones
        db.query(ChurchEvent).filter_by(source_link_id=link.id).delete()

        for ev in events_data:
            event = ChurchEvent(
                church_id=link.church_id,
                source_link_id=link.id,
                name=ev.get("name", "Unnamed Event"),
                description=ev.get("description", ""),
                event_date=ev.get("date", ""),
                event_time=ev.get("time", ""),
                location=ev.get("location", ""),
                image_url=ev.get("image_url", ""),
                source_url=link.url,
            )
            db.add(event)
            total_events += 1

        link.events_scraped_at = now

    db.commit()

    return await get_events(zip_code, db)


@router.get("/events/{zip_code}")
async def get_events(zip_code: str, db: Session = Depends(get_db)):
    churches = db.query(Church).filter_by(zip_code=zip_code).all()
    church_map = {c.id: c for c in churches}

    events = (
        db.query(ChurchEvent)
        .filter(ChurchEvent.church_id.in_([c.id for c in churches]))
        .all()
    )

    events_out = []
    for ev in events:
        church = church_map.get(ev.church_id)
        events_out.append({
            "id": ev.id,
            "church_name": church.name if church else "Unknown",
            "church_denomination": church.denomination if church else "",
            "name": ev.name,
            "description": ev.description,
            "event_date": ev.event_date,
            "event_time": ev.event_time,
            "location": ev.location,
            "image_url": ev.image_url,
            "source_url": ev.source_url,
        })

    events_out.sort(key=lambda e: e.get("event_date") or "9999-99-99")

    return {
        "zip_code": zip_code,
        "total_events": len(events_out),
        "events": events_out,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _church_dict(c: Church) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "denomination": c.denomination,
        "address": c.address,
        "discovered_at": c.discovered_at.isoformat() if c.discovered_at else None,
        "last_seen_at": c.last_seen_at.isoformat() if c.last_seen_at else None,
        "links_updated_at": c.links_updated_at.isoformat() if c.links_updated_at else None,
    }


def _church_with_links_dict(c: Church) -> dict:
    d = _church_dict(c)
    d["links"] = [
        {"id": lk.id, "url": lk.url, "platform": lk.platform}
        for lk in c.links
    ]
    return d
