from __future__ import annotations

import email
from dataclasses import dataclass
from email.header import decode_header
from email.message import Message

from imapclient import IMAPClient

from jev_mail.config import MailboxConfig

PROCESSED_KEYWORD = "$JevProcessed"


@dataclass
class Email:
    uid: int
    subject: str
    body: str

    @property
    def state(self) -> str:
        return f"Subject: {self.subject}\n\n{self.body}"


class Mailbox:
    """Thin wrapper around imapclient.IMAPClient: fetch unprocessed mail and
    tag or move messages. Use as a context manager to close the connection."""

    def __init__(self, config: MailboxConfig, server: IMAPClient | None = None, *, readonly: bool = False):
        self._config = config
        self._readonly = readonly
        # `server` is an injection point for tests; production code always
        # leaves it unset and lets __enter__ create the real connection.
        self._server = server

    def __enter__(self) -> "Mailbox":
        if self._server is None:
            self._server = IMAPClient(self._config.host, port=self._config.port, use_uid=True)
            self._server.login(self._config.username, self._config.password)
            self._server.select_folder(self._config.folder, readonly=self._readonly)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._server is not None:
            try:
                self._server.logout()
            except Exception:
                pass

    def fetch_unprocessed(self, limit: int | None = None) -> list[Email]:
        """`limit` caps how many messages get fetched+classified in one call
        -- keeps a single run/poll bounded (cost, rate limits, one huge
        backlog) instead of processing an entire inbox at once.

        IMAP UIDs increase monotonically with arrival, and SEARCH returns
        them in ascending order -- sort descending so a capped run picks up
        the newest unprocessed mail first, not whatever's oldest in a big
        backlog."""
        uids = self._server.search(["UNKEYWORD", PROCESSED_KEYWORD])
        if not uids:
            return []
        uids = sorted(uids, reverse=True)
        if limit is not None:
            uids = uids[:limit]
        response = self._server.fetch(uids, ["BODY.PEEK[]"])
        emails = []
        for uid, data in response.items():
            msg = email.message_from_bytes(data[b"BODY[]"])
            emails.append(Email(uid=uid, subject=_decode_subject(msg), body=_extract_body(msg)))
        return emails

    def mark_processed(self, uid: int) -> None:
        self._server.add_flags([uid], [PROCESSED_KEYWORD])

    def add_tag(self, uid: int, value: str) -> None:
        self._server.add_flags([uid], [value])

    def move(self, uid: int, folder: str) -> None:
        if folder not in (name for _, _, name in self._server.list_folders()):
            self._server.create_folder(folder)
        # MOVE copies flags, but the source UID disappears on success.
        self.mark_processed(uid)
        try:
            self._server.move([uid], folder)
        except Exception:
            self._server.remove_flags([uid], [PROCESSED_KEYWORD])
            raise

    def supports_idle(self) -> bool:
        return bool(self._server.has_capability("IDLE"))

    def idle(self) -> None:
        self._server.idle()

    def idle_check(self, timeout: int = 30) -> list:
        return self._server.idle_check(timeout=timeout)

    def idle_done(self) -> None:
        self._server.idle_done()


def _decode_subject(msg: Message) -> str:
    raw = msg.get("Subject", "")
    parts = decode_header(raw)
    return "".join(
        _decode_bytes(part, encoding) if isinstance(part, bytes) else part
        for part, encoding in parts
    )


def _extract_body(msg: Message) -> str:
    if msg.is_multipart():
        for content_type in ("text/plain", "text/html"):
            for part in msg.walk():
                if part.get_content_type() == content_type and not part.get_filename():
                    return _decode_payload(part)
        return ""
    return _decode_payload(msg)


def _decode_payload(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    return _decode_bytes(payload, part.get_content_charset())


def _decode_bytes(payload: bytes, charset: str | None) -> str:
    try:
        return payload.decode(charset or "utf-8", errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")
