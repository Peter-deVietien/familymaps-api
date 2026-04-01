import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import Church, ChurchEvent, ChurchLink, ZipLookup, get_db
from app.xai_client import llm_call, llm_web_search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/churchevents", tags=["churchevents"])


class ChurchesRequest(BaseModel):
    zip_code: str
    force: bool = False


# ---------------------------------------------------------------------------
# Stage 1 – Discover churches for a zip code
# ---------------------------------------------------------------------------

@router.post("/churches")
async def find_churches(req: ChurchesRequest, db: Session = Depends(get_db)):
    zip_lookup = db.query(ZipLookup).filter_by(zip_code=req.zip_code).first()

    if zip_lookup and zip_lookup.churches_updated_at and not req.force:
        churches = db.query(Church).filter_by(zip_code=req.zip_code).all()
        return {
            "zip_code": req.zip_code,
            "cached": True,
            "churches_updated_at": zip_lookup.churches_updated_at.isoformat(),
            "churches": [_church_dict(c) for c in churches],
        }

    prompt = (
        f"List all churches, places of worship, and religious organizations "
        f"located in or near zip code {req.zip_code}. For each, provide: "
        f"name, denomination (or 'non-denominational'), and street address. "
        f"Also provide the city and state for this zip code. "
        f'Return JSON in this exact format: '
        f'{{"city": "...", "state": "...", "churches": ['
        f'{{"name": "...", "denomination": "...", "address": "..."}}]}}'
    )

    try:
        data = await llm_call(prompt)
    except Exception as e:
        logger.exception("xAI call failed for Stage 1")
        raise HTTPException(status_code=502, detail=f"xAI API error: {e}")

    if req.force and zip_lookup:
        db.query(Church).filter_by(zip_code=req.zip_code).delete()

    if not zip_lookup:
        zip_lookup = ZipLookup(zip_code=req.zip_code)
        db.add(zip_lookup)

    zip_lookup.city = data.get("city", "")
    zip_lookup.state = data.get("state", "")
    zip_lookup.churches_updated_at = datetime.utcnow()

    new_churches = []
    for item in data.get("churches", []):
        church = Church(
            zip_code=req.zip_code,
            name=item.get("name", "Unknown"),
            denomination=item.get("denomination", ""),
            address=item.get("address", ""),
        )
        db.add(church)
        new_churches.append(church)

    db.commit()
    for c in new_churches:
        db.refresh(c)

    return {
        "zip_code": req.zip_code,
        "cached": False,
        "churches_updated_at": zip_lookup.churches_updated_at.isoformat(),
        "churches": [_church_dict(c) for c in new_churches],
    }


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

@router.post("/links/{zip_code}")
async def gather_links(zip_code: str, db: Session = Depends(get_db)):
    churches = db.query(Church).filter_by(zip_code=zip_code).all()
    if not churches:
        raise HTTPException(status_code=404, detail="No churches found for this zip code. Run Stage 1 first.")

    total_links = 0
    for church in churches:
        db.query(ChurchLink).filter_by(church_id=church.id).delete()

        prompt = (
            f"Search the web for '{church.name}' located at '{church.address}'. "
            f"Find all online presence: official website, Facebook page, Instagram, "
            f"YouTube, Twitter/X, event pages, community calendars. "
            f"Return a JSON array of objects with 'url' and 'platform' fields. "
            f"Example: [{{"url": "https://...", "platform": "website"}}]. "
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
            church_link = ChurchLink(
                church_id=church.id,
                url=url,
                platform=link_item.get("platform", "other"),
            )
            db.add(church_link)
            total_links += 1

        church.links_updated_at = datetime.utcnow()

    db.commit()

    churches = db.query(Church).filter_by(zip_code=zip_code).all()
    return {
        "zip_code": zip_code,
        "total_links": total_links,
        "churches": [_church_with_links_dict(c) for c in churches],
    }


# ---------------------------------------------------------------------------
# Stage 3 – Extract events from every link
# ---------------------------------------------------------------------------

@router.post("/events/{zip_code}")
async def extract_events(zip_code: str, db: Session = Depends(get_db)):
    churches = db.query(Church).filter_by(zip_code=zip_code).all()
    if not churches:
        raise HTTPException(status_code=404, detail="No churches found. Run Stage 1 first.")

    all_links = []
    for church in churches:
        links = db.query(ChurchLink).filter_by(church_id=church.id).all()
        all_links.extend(links)

    if not all_links:
        raise HTTPException(status_code=404, detail="No links found. Run Stage 2 first.")

    db.query(ChurchEvent).filter(
        ChurchEvent.church_id.in_([c.id for c in churches])
    ).delete(synchronize_session=False)

    total_events = 0
    for link in all_links:
        prompt = (
            f"Visit this URL: {link.url}\n"
            f"Extract all upcoming events, services, or gatherings from this page. "
            f"For each event, provide: name, description, date (ISO format YYYY-MM-DD if possible), "
            f"time, location, and any image URL. "
            f"Return a JSON array of objects. If no events are found, return an empty array [].\n"
            f"Example: [{{"name": "...", "description": "...", "date": "2025-06-15", "time": "10:00 AM", "location": "...", "image_url": ""}}]"
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

        link.events_scraped_at = datetime.utcnow()

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
        "links_updated_at": c.links_updated_at.isoformat() if c.links_updated_at else None,
    }


def _church_with_links_dict(c: Church) -> dict:
    d = _church_dict(c)
    d["links"] = [
        {"id": lk.id, "url": lk.url, "platform": lk.platform}
        for lk in c.links
    ]
    return d
