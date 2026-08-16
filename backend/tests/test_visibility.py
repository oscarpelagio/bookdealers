"""Tests de las reglas de visibilidad (core.visibility)."""

import uuid

from app.core.visibility import is_visible
from app.enums import Visibility

AUTHOR = uuid.uuid4()
VIEWER = uuid.uuid4()
OTHER = uuid.uuid4()


def test_author_always_sees_own_content():
    for section in Visibility:
        assert is_visible(section, viewer_id=AUTHOR, author_id=AUTHOR) is True


def test_public_visible_to_anyone():
    assert is_visible(Visibility.PUBLIC, viewer_id=OTHER, author_id=AUTHOR) is True


def test_private_only_author():
    assert is_visible(Visibility.PRIVATE, viewer_id=OTHER, author_id=AUTHOR) is False
    assert is_visible(Visibility.PRIVATE, viewer_id=VIEWER, author_id=AUTHOR) is False
    assert is_visible(Visibility.PRIVATE, viewer_id=AUTHOR, author_id=AUTHOR) is True


def test_followers_visible_to_followers_and_author():
    assert (
        is_visible(
            Visibility.FOLLOWERS, viewer_id=VIEWER, author_id=AUTHOR, is_follower=True
        )
        is True
    )
    assert (
        is_visible(Visibility.FOLLOWERS, viewer_id=OTHER, author_id=AUTHOR) is False
    )


def test_block_hides_content_even_if_public():
    assert (
        is_visible(
            Visibility.PUBLIC,
            viewer_id=VIEWER,
            author_id=AUTHOR,
            is_blocked=True,
        )
        is False
    )


def test_inactive_author_hidden():
    assert (
        is_visible(
            Visibility.PUBLIC, viewer_id=OTHER, author_id=AUTHOR, author_active=False
        )
        is False
    )
    # Ni el propio autor ve contenido de una cuenta inactiva.
    assert (
        is_visible(
            Visibility.PUBLIC, viewer_id=AUTHOR, author_id=AUTHOR, author_active=False
        )
        is False
    )


def test_anonymous_viewer():
    assert is_visible(Visibility.PUBLIC, viewer_id=None, author_id=AUTHOR) is True
    assert is_visible(Visibility.PRIVATE, viewer_id=None, author_id=AUTHOR) is False
