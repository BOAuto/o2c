import imaplib

from app.temporal.imap_pool import _is_transport_failure


def test_imap_abort_is_transport() -> None:
    assert _is_transport_failure(imaplib.IMAP4.abort("socket error: EOF"))


def test_broken_pipe_is_transport() -> None:
    assert _is_transport_failure(BrokenPipeError())


def test_value_error_not_transport() -> None:
    assert not _is_transport_failure(ValueError("invalid"))
