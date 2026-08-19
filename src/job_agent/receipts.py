from __future__ import annotations

import email
import imaplib
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.message import Message
from typing import Any


POSITIVE_KEYWORDS = ("申请成功", "投递成功", "收到您的简历", "application received", "thank you for applying")
NEGATIVE_KEYWORDS = ("很遗憾", "不匹配", "未通过", "not moving forward", "unfortunately")


@dataclass(slots=True)
class Receipt:
    matched: bool
    positive: bool
    subject: str = ""
    sender: str = ""
    date: str = ""
    evidence: str = ""


def _decode(value: str | None) -> str:
    return str(make_header(decode_header(value or "")))


def _message_text(message: Message) -> str:
    parts: list[str] = []
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() != "text/plain" or "attachment" in str(part.get("Content-Disposition", "")):
                continue
            charset = part.get_content_charset() or "utf-8"
            parts.append(part.get_payload(decode=True).decode(charset, errors="replace"))
    else:
        charset = message.get_content_charset() or "utf-8"
        payload = message.get_payload(decode=True)
        if payload:
            parts.append(payload.decode(charset, errors="replace"))
    return "\n".join(parts)


class ImapReceiptChecker:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def find(self, company: str, title: str, since: datetime) -> Receipt:
        password = os.getenv(str(self.config.get("password_env", "JOB_AGENT_IMAP_PASSWORD")))
        if not password:
            raise RuntimeError("IMAP password environment variable is not set")
        host = str(self.config["host"])
        port = int(self.config.get("port", 993))
        username = str(self.config["username"])
        folder = str(self.config.get("folder", "INBOX"))
        with imaplib.IMAP4_SSL(host, port) as client:
            client.login(username, password)
            client.select(folder, readonly=True)
            date_key = since.astimezone(timezone.utc).strftime("%d-%b-%Y")
            status, data = client.search(None, "SINCE", date_key)
            if status != "OK":
                raise RuntimeError("IMAP search failed")
            for message_id in reversed(data[0].split()[-200:]):
                status, payload = client.fetch(message_id, "(RFC822)")
                if status != "OK" or not payload or not isinstance(payload[0], tuple):
                    continue
                message = email.message_from_bytes(payload[0][1])
                subject = _decode(message.get("Subject"))
                sender = _decode(message.get("From"))
                body = _message_text(message)[:10000]
                haystack = f"{subject}\n{sender}\n{body}".lower()
                identity_match = company.lower() in haystack or title.lower() in haystack
                positive = any(keyword.lower() in haystack for keyword in POSITIVE_KEYWORDS)
                negative = any(keyword.lower() in haystack for keyword in NEGATIVE_KEYWORDS)
                if identity_match and (positive or negative):
                    return Receipt(True, positive and not negative, subject, sender, _decode(message.get("Date")), body[:240])
        return Receipt(False, False)
