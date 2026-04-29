"""Parse mail messages for O2C ingestion (headers, HTML, non-image attachments)."""

from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup
from imap_tools import MailAttachment, MailMessage
from imap_tools.utils import parse_email_addresses


def normalize_message_id(value: str | None) -> str:
    if not value:
        return ""
    s = value.strip()
    s = re.sub(r"^[<>]+|[<>]+$", "", s)
    #return s.strip().lower()
    return s.strip()


def sanitize_msg_id(msg_id: str | list[str] | tuple[str, ...] | None) -> str:
    if not msg_id:
        return ""
    if isinstance(msg_id, (tuple, list)):
        msg_id = msg_id[0] if msg_id else ""
    s = str(msg_id).strip()
    s = s.replace('"', "")
    return s.strip()


def primary_email_from_header(from_header: str) -> str:
    if not from_header:
        return ""
    for addr in parse_email_addresses(from_header):
        if addr.email:
            return addr.email.strip().lower()
    return ""


def email_domain(email: str) -> str:
    val = (email or "").strip().lower()
    if "@" not in val:
        return ""
    return val.split("@", 1)[1].strip()


def get_header_single(msg: MailMessage, header_name: str) -> str | None:
    if not header_name:
        return None
    vals = None
    for k, v in msg.headers.items():
        if str(k).strip().lower() == str(header_name).strip().lower():
            vals = v
            break
    if vals is None:
        return None
    if not vals:
        return None
    return vals[0].strip() if vals[0] else None


def cc_formatted_for_storage(msg: MailMessage) -> str:
    parts: list[str] = []
    for addr in msg.cc_values:
        if addr.name and addr.email:
            parts.append(f"{addr.name} <{addr.email}>")
        elif addr.email:
            parts.append(addr.email)
    return json.dumps(parts)


def _is_non_image_attachment(att: MailAttachment) -> bool:
    ct = (att.content_type or "").lower()
    if ct.startswith("image/"):
        return False
    if att.content_id and att.content_disposition == "inline":
        return False
    return True


def list_non_image_attachments(msg: MailMessage) -> list[MailAttachment]:
    return [a for a in msg.attachments if _is_non_image_attachment(a)]


def render_html_document(msg: MailMessage) -> str:
    """Build a standalone HTML document for the message body (simplified vs legacy script)."""
    clean_body = msg.html or f"<pre>{msg.text or ''}</pre>"
    if msg.html:
        soup = BeautifulSoup(msg.html, "html.parser")
        for tag in soup(["script", "style", "meta", "link"]):
            tag.decompose()
        clean_body = str(soup)
    subj = msg.subject or ""
    from_ = msg.from_ or ""
    to_parts = ", ".join(
        f"{a.name} <{a.email}>" if a.name and a.email else (a.email or "")
        for a in msg.to_values
    )
    cc_s = cc_formatted_for_storage(msg)
    cc_list = json.loads(cc_s) if cc_s else []
    cc_line = ", ".join(cc_list) if cc_list else ""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{subj}</title></head>
<body>
<p><b>{subj}</b></p>
<p>From: {from_}<br>To: {to_parts}<br>{"CC: " + cc_line + "<br>" if cc_line else ""}Date: {msg.date_str}</p>
<hr>
<div>{clean_body}</div>
</body></html>"""


def html_for_po_attachment(msg: MailMessage) -> str:
    """HTML snapshot for external correspondent when no file attachments on anchor."""
    return render_html_document(msg)
