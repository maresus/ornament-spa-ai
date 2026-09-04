from __future__ import annotations
import os, smtplib, uuid
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
from pydantic import BaseModel
from app.chat.llm_chat import chat

router = APIRouter(prefix="/chat", tags=["chat"])
admin_router = APIRouter(tags=["admin"])

_sessions: dict[str, dict] = {}
_conversations: list[dict] = []
_inquiries: list[dict] = []
_MAX_STORED = 5000


def _seed() -> None:
    now = datetime.now(timezone.utc)
    def dt(days_ago: int, hour: int = 10, minute: int = 0) -> str:
        d = now - timedelta(days=days_ago)
        return d.replace(hour=hour, minute=minute, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    def uid() -> str:
        return str(uuid.uuid4())[:8]

    _inquiries.extend([
        # M. Horvat — 4 obiski (Access Bars redna gostja)
        {"id":uid(),"ime":"Marija Horvat","telefon":"041 123 456","email":"m.horvat@gmail.com","tip":"Access Bars®","sporocilo":"Priporočila mi je prijateljica.","status":"koncano","admin_notes":"","created_at":dt(152,9,0)},
        {"id":uid(),"ime":"Marija Horvat","telefon":"041 123 456","email":"m.horvat@gmail.com","tip":"Access Bars®","sporocilo":"","status":"koncano","admin_notes":"","created_at":dt(121,10,0)},
        {"id":uid(),"ime":"Marija Horvat","telefon":"041 123 456","email":"m.horvat@gmail.com","tip":"Masaža hrbta","sporocilo":"","status":"koncano","admin_notes":"","created_at":dt(88,11,0)},
        {"id":uid(),"ime":"Marija Horvat","telefon":"041 123 456","email":"m.horvat@gmail.com","tip":"Access Bars®","sporocilo":"","status":"potrjeno","admin_notes":"","created_at":dt(3,10,0)},
        # A. Kovačič — 3 obiski
        {"id":uid(),"ime":"Ana Kovačič","telefon":"031 234 567","email":"","tip":"Masaža hrbta","sporocilo":"","status":"koncano","admin_notes":"","created_at":dt(145,14,0)},
        {"id":uid(),"ime":"Ana Kovačič","telefon":"031 234 567","email":"","tip":"Masaža celega telesa","sporocilo":"","status":"koncano","admin_notes":"","created_at":dt(90,15,0)},
        {"id":uid(),"ime":"Ana Kovačič","telefon":"031 234 567","email":"","tip":"Masaža hrbta","sporocilo":"","status":"potrjeno","admin_notes":"","created_at":dt(5,14,0)},
        # T. Novak — 3 obiski (wellness za dva)
        {"id":uid(),"ime":"Tanja Novak","telefon":"070 345 678","email":"tnovak@outlook.com","tip":"Zasebni wellness za 2","sporocilo":"Za obletnico.","status":"koncano","admin_notes":"","created_at":dt(130,17,0)},
        {"id":uid(),"ime":"Tanja Novak","telefon":"070 345 678","email":"tnovak@outlook.com","tip":"Romantični paket za para","sporocilo":"","status":"koncano","admin_notes":"","created_at":dt(70,18,0)},
        {"id":uid(),"ime":"Tanja Novak","telefon":"070 345 678","email":"tnovak@outlook.com","tip":"Zasebni wellness za 2","sporocilo":"","status":"caka","admin_notes":"","created_at":dt(1,16,0)},
        # J. Štefančič — 2 obiski
        {"id":uid(),"ime":"Janez Štefančič","telefon":"040 456 789","email":"","tip":"Masaža hrbta","sporocilo":"","status":"koncano","admin_notes":"","created_at":dt(110,11,0)},
        {"id":uid(),"ime":"Janez Štefančič","telefon":"040 456 789","email":"","tip":"Antistresna masaža hrbta in glave","sporocilo":"Stres v službi.","status":"koncano","admin_notes":"","created_at":dt(22,11,0)},
        # N. Vidmar — 2 obiski
        {"id":uid(),"ime":"Nataša Vidmar","telefon":"051 567 890","email":"n.vidmar@gmail.com","tip":"Masaža za nosečnice","sporocilo":"","status":"koncano","admin_notes":"","created_at":dt(95,10,0)},
        {"id":uid(),"ime":"Nataša Vidmar","telefon":"051 567 890","email":"n.vidmar@gmail.com","tip":"Masaža celega telesa","sporocilo":"","status":"potrjeno","admin_notes":"","created_at":dt(8,10,0)},
        # enkratni obiski
        {"id":uid(),"ime":"Boštjan Režek","telefon":"064 678 901","email":"","tip":"Najem e-kolesa","sporocilo":"2 odrasli kolesi za en dan.","status":"koncano","admin_notes":"","created_at":dt(60,9,0)},
        {"id":uid(),"ime":"Sara Lenart","telefon":"068 789 012","email":"sara.lenart@gmail.com","tip":"Access Bars® za otroka","sporocilo":"Otrok 8 let, ADHD.","status":"koncano","admin_notes":"","created_at":dt(44,10,0)},
        {"id":uid(),"ime":"David Mohor","telefon":"041 890 123","email":"","tip":"Masaža stopal","sporocilo":"","status":"koncano","admin_notes":"","created_at":dt(33,16,0)},
        {"id":uid(),"ime":"Petra Hren","telefon":"031 901 234","email":"phren@gmail.com","tip":"Zasebni wellness za 2","sporocilo":"Za rojstni dan.","status":"koncano","admin_notes":"","created_at":dt(27,15,0)},
        {"id":uid(),"ime":"Eva Gorenc","telefon":"070 012 345","email":"","tip":"Masaža hrbta","sporocilo":"","status":"koncano","admin_notes":"","created_at":dt(18,11,0)},
        {"id":uid(),"ime":"Luka Černe","telefon":"040 123 456","email":"l.cerne@gmail.com","tip":"Masaža celega telesa","sporocilo":"Priporočila mi prijateljica.","status":"potrjeno","admin_notes":"","created_at":dt(12,14,0)},
        {"id":uid(),"ime":"Vida Tomšič","telefon":"051 234 567","email":"","tip":"Masaža obraza in glave","sporocilo":"","status":"potrjeno","admin_notes":"","created_at":dt(6,10,0)},
        {"id":uid(),"ime":"Robert Bratina","telefon":"064 345 678","email":"rbratina@gmail.com","tip":"Zasebni wellness za 2","sporocilo":"Dekliščina za 4 osebe.","status":"caka","admin_notes":"Preveriti — morda skupinski najem.","created_at":dt(2,9,0)},
        {"id":uid(),"ime":"Katja Zupanc","telefon":"068 456 789","email":"","tip":"Masaža hrbta","sporocilo":"","status":"caka","admin_notes":"","created_at":dt(0,8,30)},
    ])

    sid1, sid2, sid3, sid4, sid5 = [str(uuid.uuid4()) for _ in range(5)]
    _conversations.extend([
        {"session_id":sid1,"user_message":"Koliko stane masaža hrbta?","bot_response":"Masaža hrbta traja 25 minut in stane 33 EUR. Zajema hrbet, ramena in vrat.\n\nZa rezervacijo pokličite 031 683 787 ali pišite na info@ornamentspa.eu.","created_at":dt(1,21,14)},
        {"session_id":sid1,"user_message":"In masaža celega telesa?","bot_response":"Masaža celega telesa traja 50 minut in stane 57 EUR. Odpravlja napetost po celem telesu.\n\nZa rezervacijo pokličite 031 683 787.","created_at":dt(1,21,16)},
        {"session_id":sid2,"user_message":"Ali imate prosto v soboto zvečer za dva?","bot_response":"Za razpoložljivost terminov nas pokličite na 031 683 787 ali pišite na info@ornamentspa.eu. Rezervirate lahko tudi prek spletne strani ornamentspa.eu (15% popust pri prvi spletni rezervaciji).","created_at":dt(2,18,2)},
        {"session_id":sid3,"user_message":"Ali je savna primerna v nosečnosti?","bot_response":"Tega podatka nimam. Za podrobnosti pokličite 031 683 787 ali pišite na info@ornamentspa.eu.","created_at":dt(3,14,30)},
        {"session_id":sid4,"user_message":"Ali lahko darilni bon kupim po spletu?","bot_response":"Da, darilni bon naročite prek e-pošte info@ornamentspa.eu ali na telefonski številki 031 683 787.\n\n- Vrednost: določite jo sami\n- Veljavnost: 1 leto od nakupa\n- Dostava: po e-pošti brezplačno ali po pošti (3 EUR doplačilo)","created_at":dt(4,11,5)},
        {"session_id":sid5,"user_message":"Imate kakšen paket za podjetja, za ekipo 8 ljudi?","bot_response":"Tega podatka nimam. Za podrobnosti pokličite 031 683 787 ali pišite na info@ornamentspa.eu.","created_at":dt(5,16,20)},
        {"session_id":sid5,"user_message":"Ok hvala","bot_response":"Z veseljem! Če boste imeli še kakšno vprašanje, sem tu.","created_at":dt(5,16,22)},
    ])


_seed()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ornament2026")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)

BRAND = "#824D88"
BRAND_DARK = "#6a3d70"


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str

class InquiryRequest(BaseModel):
    ime: str
    telefon: str
    email: str | None = None
    sporocilo: str | None = None
    tip: str | None = None

class InquiryUpdate(BaseModel):
    status: str | None = None
    admin_notes: str | None = None

class EmailToClient(BaseModel):
    subject: str
    body: str


def _send_email(to: str, subject: str, html: str) -> bool:
    if not SMTP_HOST or not SMTP_USER or not to:
        print(f"[email] SMTP ni konfiguriran — preskočeno")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = FROM_EMAIL
        msg["To"] = to
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(FROM_EMAIL, to, msg.as_string())
        return True
    except Exception as e:
        print(f"[email] Napaka: {e}")
        return False


def _check_admin(key: str) -> None:
    if key != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _get_session(session_id: str | None) -> tuple[str, dict]:
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]
    new_id = session_id or str(uuid.uuid4())
    _sessions[new_id] = {"history": [], "started": datetime.now(timezone.utc).isoformat()}
    return new_id, _sessions[new_id]


def _log_conversation(session_id: str, user_msg: str, bot_reply: str) -> None:
    global _conversations
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    _conversations.append({"session_id": session_id, "user_message": user_msg, "bot_response": bot_reply, "created_at": ts})
    if len(_conversations) > _MAX_STORED:
        _conversations = _conversations[-_MAX_STORED:]


@router.post("", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    session_id, session = _get_session(payload.session_id)
    message = payload.message.strip()
    result = chat(message=message, history=session["history"])
    session["history"].append({"role": "user", "content": message})
    session["history"].append({"role": "assistant", "content": result["reply"]})
    if len(session["history"]) > 20:
        session["history"] = session["history"][-20:]
    _log_conversation(session_id, message, result["reply"])
    return ChatResponse(reply=result["reply"], session_id=session_id)


@router.post("/inquiry")
async def submit_inquiry(payload: InquiryRequest):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    inq_id = str(uuid.uuid4())[:8]
    _inquiries.append({
        "id": inq_id,
        "ime": payload.ime,
        "telefon": payload.telefon,
        "email": payload.email,
        "tip": payload.tip or "-",
        "sporocilo": payload.sporocilo or "-",
        "status": "caka",
        "admin_notes": "",
        "created_at": ts
    })

    admin_html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
    <div style="background:{BRAND};padding:24px;border-radius:8px 8px 0 0;">
      <h2 style="color:#fff;margin:0;">Novo povpraševanje — Ornament Spa</h2>
      <p style="color:rgba(255,255,255,0.9);margin:4px 0 0;">{ts} UTC</p>
    </div>
    <div style="background:#f8f9fa;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 8px 8px;">
      <table style="width:100%;border-collapse:collapse;">
        <tr><td style="padding:8px 0;color:#666;width:140px;"><b>Ime</b></td><td>{payload.ime}</td></tr>
        <tr><td style="padding:8px 0;color:#666;"><b>Telefon</b></td><td><a href="tel:{payload.telefon}" style="color:{BRAND};">{payload.telefon}</a></td></tr>
        <tr><td style="padding:8px 0;color:#666;"><b>Email</b></td><td>{f'<a href="mailto:{payload.email}" style="color:{BRAND};">{payload.email}</a>' if payload.email else "-"}</td></tr>
        <tr><td style="padding:8px 0;color:#666;"><b>Storitev</b></td><td>{payload.tip or "-"}</td></tr>
        <tr><td style="padding:8px 0;color:#666;vertical-align:top;"><b>Sporočilo</b></td><td>{payload.sporocilo or "-"}</td></tr>
      </table>
    </div>
    </body></html>"""
    _send_email(ADMIN_EMAIL, f"Povpraševanje Ornament Spa: {payload.ime}", admin_html)

    confirm_html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
    <div style="background:{BRAND};padding:24px;border-radius:8px 8px 0 0;">
      <h2 style="color:#fff;margin:0;">Hvala za povpraševanje, {payload.ime}!</h2>
      <p style="color:rgba(255,255,255,0.9);margin:4px 0 0;">Wellness Ornament Spa — Vaša oaza sprostitve</p>
    </div>
    <div style="background:#f8f9fa;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 8px 8px;">
      <p>Prejeli smo vaše povpraševanje. Naša ekipa vas bo kontaktirala v najkrajšem možnem času.</p>
      <div style="background:{BRAND};color:#fff;padding:16px;border-radius:8px;margin:20px 0;">
        <b>Naši kontakti:</b><br>
        Tel: 031 683 787<br>
        Email: info@ornamentspa.eu<br>
        Splet: ornamentspa.eu
      </div>
      <p style="color:#999;font-size:12px;">Wellness Ornament, Katrin Vidnar s.p. · Ljubljanska cesta 10, Kostanjevica na Krki</p>
    </div>
    </body></html>"""
    if payload.email:
        _send_email(payload.email, "Potrditev rezervacije — Ornament Spa", confirm_html)
    return {"ok": True, "id": inq_id}


# ── ADMIN PANEL ──────────────────────────────────────────────────────────────

@admin_router.get("/admin", response_class=HTMLResponse)
def admin_panel():
    admin_html_path = Path(__file__).parent.parent.parent / "static" / "admin.html"
    if admin_html_path.exists():
        html = admin_html_path.read_text(encoding="utf-8")
        return HTMLResponse(content=html)
    return HTMLResponse(content="<h1>Admin panel se nalaga...</h1>")


@admin_router.get("/api/admin/inquiries")
def get_inquiries(key: str = Query(default=""), status: str = Query(default=""), tip: str = Query(default=""), hours: int = Query(default=0)):
    _check_admin(key)
    result = list(_inquiries)
    if hours > 0:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        result = [i for i in result if i.get("created_at", "") >= cutoff]
    if status:
        result = [i for i in result if i.get("status") == status]
    if tip:
        result = [i for i in result if tip.lower() in (i.get("tip") or "").lower()]
    return {"inquiries": list(reversed(result)), "total": len(result)}


@admin_router.patch("/api/admin/inquiries/{inq_id}")
def update_inquiry(inq_id: str, payload: InquiryUpdate, key: str = Query(default="")):
    _check_admin(key)
    for inq in _inquiries:
        if inq.get("id") == inq_id:
            if payload.status is not None:
                inq["status"] = payload.status
            if payload.admin_notes is not None:
                inq["admin_notes"] = payload.admin_notes
            inq["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            return {"ok": True, "inquiry": inq}
    raise HTTPException(status_code=404, detail="Povpraševanje ni najdeno")


@admin_router.post("/api/admin/inquiries/{inq_id}/email")
def send_email_to_client(inq_id: str, payload: EmailToClient, key: str = Query(default="")):
    _check_admin(key)
    inq = next((i for i in _inquiries if i.get("id") == inq_id), None)
    if not inq:
        raise HTTPException(status_code=404, detail="Povpraševanje ni najdeno")
    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
    <div style="background:{BRAND};padding:24px;border-radius:8px 8px 0 0;">
      <h2 style="color:#fff;margin:0;">Wellness Ornament Spa</h2>
    </div>
    <div style="background:#f8f9fa;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 8px 8px;">
      <p style="white-space:pre-wrap;">{payload.body}</p>
      <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
      <p style="color:#999;font-size:12px;">Wellness Ornament, Katrin Vidnar s.p. · Ljubljanska cesta 10, Kostanjevica na Krki · 031 683 787</p>
    </div>
    </body></html>"""
    sent = _send_email(inq["email"], payload.subject, html)
    return {"ok": sent}


@admin_router.get("/api/admin/stats")
def get_stats(key: str = Query(default="")):
    _check_admin(key)
    now = datetime.now(timezone.utc)
    def ts_filter(hours):
        cutoff = (now - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        return [i for i in _inquiries if i.get("created_at", "") >= cutoff]
    danes = ts_filter(24)
    teden = ts_filter(168)
    mesec = ts_filter(720)
    statusi = {"caka": 0, "potrjeno": 0, "zavrnjeno": 0}
    for i in _inquiries:
        s = i.get("status", "caka")
        statusi[s] = statusi.get(s, 0) + 1
    storitve: dict = {}
    for i in _inquiries:
        t = i.get("tip") or "Neznano"
        storitve[t] = storitve.get(t, 0) + 1
    return {
        "danes": len(danes),
        "teden": len(teden),
        "mesec": len(mesec),
        "skupaj": len(_inquiries),
        "statusi": statusi,
        "storitve": storitve,
    }


@admin_router.get("/api/admin/conversations")
def get_conversations(key: str = Query(default=""), hours: int = Query(default=24)):
    _check_admin(key)
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    filtered = [c for c in _conversations if c.get("created_at", "") >= cutoff]
    return {"conversations": list(reversed(filtered)), "total": len(filtered)}


# ── PANEL V2 ─────────────────────────────────────────────────────────────────

@admin_router.get("/panel", response_class=HTMLResponse)
def panel_page():
    panel_html_path = Path(__file__).parent.parent.parent / "static" / "panel.html"
    if panel_html_path.exists():
        html = panel_html_path.read_text(encoding="utf-8")
        return HTMLResponse(content=html)
    return HTMLResponse(content="<h1>Panel se nalaga...</h1>")


def _initials(ime: str) -> str:
    parts = ime.strip().split()
    if not parts:
        return "?"
    return ". ".join(p[0].upper() for p in parts if p) + "."


@admin_router.get("/api/panel/rezervacije")
def panel_rezervacije(key: str = Query(default=""), od: str = Query(default=""), do: str = Query(default="")):
    _check_admin(key)
    result = list(_inquiries)
    if od:
        result = [i for i in result if i.get("created_at", "") >= od]
    if do:
        result = [i for i in result if i.get("created_at", "") <= do]
    def fmt(inq):
        return {
            "id": inq["id"],
            "ime": _initials(inq.get("ime", "")),
            "tip": inq.get("tip", "-"),
            "status": inq.get("status", "caka"),
            "created_at": inq.get("created_at", ""),
            "admin_notes": inq.get("admin_notes", ""),
        }
    return {"rezervacije": [fmt(i) for i in reversed(result)], "total": len(result)}


@admin_router.get("/api/panel/trend")
def panel_trend(key: str = Query(default=""), mesecev: int = Query(default=6)):
    _check_admin(key)
    now = datetime.now(timezone.utc)
    meseci = ["jan","feb","mar","apr","maj","jun","jul","avg","sep","okt","nov","dec"]
    result = []
    for i in range(mesecev - 1, -1, -1):
        m = now.month - i
        y = now.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        prefix = f"{y}-{m:02d}"
        count = sum(1 for inq in _inquiries if inq.get("created_at", "").startswith(prefix))
        result.append([meseci[m - 1], count, 0, count])
    return {"trend": result}


@admin_router.get("/api/panel/gostje")
def panel_gostje(key: str = Query(default="")):
    _check_admin(key)
    by_phone: dict = {}
    for inq in _inquiries:
        phone = (inq.get("telefon") or "").strip()
        if not phone:
            continue
        by_phone.setdefault(phone, []).append(inq)

    stalni = []
    for phone, inqs in by_phone.items():
        tips = [i.get("tip", "") for i in inqs if i.get("tip") and i.get("tip") != "-"]
        najljub = max(set(tips), key=tips.count) if tips else "-"
        last = sorted(inqs, key=lambda x: x.get("created_at", ""))[-1]
        last_date = last.get("created_at", "")[:10]
        stalni.append({
            "ime": _initials(inqs[0].get("ime", "")),
            "obiski": len(inqs),
            "najljub": najljub,
            "zadnji": last_date,
            "segment": "Redna nega",
        })
    stalni.sort(key=lambda x: x["obiski"], reverse=True)

    novi = sum(1 for inqs in by_phone.values() if len(inqs) == 1)
    vrnjeni = sum(1 for inqs in by_phone.values() if len(inqs) > 1)
    return {
        "stalni": stalni[:10],
        "segmenti": [],
        "viri_zvestoba": [],
        "gostje": {"novi": novi, "vrnjeni": vrnjeni, "pogostost": "-", "zadrzanje": "-"},
    }


@admin_router.get("/api/panel/pogovori")
def panel_pogovori(key: str = Query(default=""), limit: int = Query(default=20)):
    _check_admin(key)
    sessions: dict = {}
    for conv in _conversations:
        sid = conv.get("session_id", "")
        sessions.setdefault(sid, []).append(conv)

    result = []
    sorted_sessions = sorted(sessions.items(),
                              key=lambda x: x[1][-1].get("created_at", ""),
                              reverse=True)[:limit]
    for sid, msgs in sorted_sessions:
        first_user = msgs[0].get("user_message", "") if msgs else ""
        last_time = msgs[-1].get("created_at", "") if msgs else ""
        has_fallback = any("nimam podatka" in m.get("bot_response", "").lower() or
                           "to ni moje področje" in m.get("bot_response", "").lower()
                           for m in msgs)
        pairs = []
        for m in msgs:
            pairs.append(["gost", m.get("user_message", "")])
            pairs.append(["bot", m.get("bot_response", "")])
        result.append({
            "c": last_time,
            "v": first_user[:80],
            "o": 0 if has_fallback else 1,
            "p": pairs,
        })
    return {"pogovori": result}


@admin_router.get("/api/panel/vprasanja")
def panel_vprasanja(key: str = Query(default=""), obdobje: str = Query(default="teden")):
    _check_admin(key)
    from collections import Counter
    msgs = [c.get("user_message", "").strip() for c in _conversations if c.get("user_message")]
    counter = Counter(msgs)
    result = [[msg, count, 0] for msg, count in counter.most_common(10) if msg]
    return {"vprasanja": result}


_OBJAVE = {
    "teden": [
        ["Zasebni wellness za dva — nedeljski večer", "Instagram", "zn",   4820, 312, 41],
        ["Access Bars® — kaj sploh je",               "Facebook",  "zn v", 2140,  96, 17],
        ["Jutranja savna — zakaj deluje",             "Instagram", "zn",   1780,  74,  6],
    ],
    "prej": [
        ["Darilni bon za rojstni dan", "Facebook",  "zn v", 1920, 88, 14],
        ["Nova terapija Access Lift",  "Instagram", "zn",   2260, 131, 11],
    ],
    "mesec": [
        ["Zasebni wellness za dva — nedeljski večer", "Instagram", "zn",   4820, 312, 41],
        ["Nova terapija Access Lift",                 "Instagram", "zn",   2260, 131, 11],
        ["Darilni bon za rojstni dan",                "Facebook",  "zn v", 1920,  88, 14],
        ["Access Bars® — kaj sploh je",               "Facebook",  "zn v", 2140,  96, 17],
    ],
}


@admin_router.get("/api/panel/objave")
def panel_objave(key: str = Query(default=""), obdobje: str = Query(default="teden")):
    _check_admin(key)
    return {"objave": _OBJAVE.get(obdobje, [])}


_OGLASI = {
    "teden": [["Zasebni wellness — pari", 64, 9], ["Darilni boni", 38, 4], ["Masaže — splošno", 22, 1]],
    "prej":  [["Zasebni wellness — pari", 60, 7], ["Darilni boni", 40, 3], ["Masaže — splošno", 25, 1]],
    "mesec": [["Zasebni wellness — pari", 248, 34], ["Darilni boni", 152, 15], ["Masaže — splošno", 96, 5]],
}


@admin_router.get("/api/panel/oglasi")
def panel_oglasi(key: str = Query(default=""), obdobje: str = Query(default="teden")):
    _check_admin(key)
    return {"oglasi": _OGLASI.get(obdobje, [])}


@admin_router.get("/api/panel/predlogi")
def panel_predlogi(key: str = Query(default="")):
    _check_admin(key)
    return {"predlogi": [
        ["Odstavek o savni v nosečnosti", "Redno vprašanje, na katero pomočnik nima odgovora"],
        ["Ponudba paketov za podjetja", "Pogosto vprašano, ponudbe za podjetja še ni"],
        ["Objava v nedeljo zvečer", "Takrat je največ rezervacij, objav pa nobene"],
    ]}
