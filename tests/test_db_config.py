"""How the app decides which database to talk to.

The silent SQLite fallback is a convenience locally and a trap in production:
a deployment with no DATABASE_URL does not fail at boot, it serves every page
that renders a form and returns 500 on every page that runs a query, with
"no such table: vehicles" buried in the logs. These tests pin the fallback to
the case it was meant for.
"""

from __future__ import annotations

import pytest

from rental.db import DEFAULT_SQLITE_URL, get_database_url


def test_an_explicit_url_is_used_as_given(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pw@host/db")
    assert get_database_url() == "postgresql+psycopg://user:pw@host/db"


def test_neon_url_forms_are_rewritten_for_psycopg3(monkeypatch):
    """Neon hands out postgres:// and postgresql://; SQLAlchemy needs the driver."""
    for given in ("postgres://u:p@h/d", "postgresql://u:p@h/d"):
        monkeypatch.setenv("DATABASE_URL", given)
        assert get_database_url() == "postgresql+psycopg://u:p@h/d"


def test_no_url_falls_back_to_sqlite_when_running_locally(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    assert get_database_url() == DEFAULT_SQLITE_URL


def test_no_url_on_vercel_raises_instead_of_falling_back(monkeypatch):
    """The production misconfiguration must announce itself, not degrade quietly.

    Falling back to SQLite here is what produced a live 500 on every page that
    queried a vehicle while the login page rendered perfectly -- a failure that
    looks like a code bug and is not one.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    with pytest.raises(RuntimeError) as excinfo:
        get_database_url()
    message = str(excinfo.value)
    assert "DATABASE_URL" in message
    assert "SQLite" in message


def test_an_empty_url_on_vercel_is_treated_as_missing(monkeypatch):
    """An env var set to the empty string is the shape a blank dashboard field takes."""
    monkeypatch.setenv("DATABASE_URL", "   ")
    monkeypatch.setenv("VERCEL", "1")
    with pytest.raises(RuntimeError):
        get_database_url()
