import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse
from django.test import SimpleTestCase

import fAIth.bible_globals as bible_globals
from frontend.views import main_site


def reset_globals(enabled_versions, default_version, default_book, default_chapter):
    """Reset the globals to their default values."""

    # Reset the globals to their default values
    bible_globals.BIBLE_DATA_ROOT = None
    bible_globals.DEFAULT_VERSION = ""
    bible_globals.DEFAULT_BOOK = ""
    bible_globals.DEFAULT_CHAPTER = ""
    bible_globals.VERSION_SELECTION = []
    bible_globals.IN_ORDER_BOOKS = []
    bible_globals.CHAPTER_SELECTION = {}
    bible_globals.ALL_VERSES = {}

    # Set the environment variables
    os.environ["ENABLED_VERSIONS"] = enabled_versions
    os.environ["DEFAULT_VERSION"] = default_version
    os.environ["DEFAULT_BOOK"] = default_book
    os.environ["DEFAULT_CHAPTER"] = default_chapter

    # Initialize all globals
    bible_globals.set_bible_data_root()
    bible_globals.set_version_selection()
    bible_globals.set_default_version()
    bible_globals.set_in_order_books()
    bible_globals.set_default_book()
    bible_globals.set_chapter_selection()
    bible_globals.set_default_chapter()
    bible_globals.set_all_verses()


def add_auser(request, user=None):
    """
    Give a bare request the auser() method that AuthenticationMiddleware normally adds.

    full_view awaits request.auser() to load the notes. Defaults to a signed-out visitor.
    """
    if user is None:
        user = AnonymousUser()

    async def auser():
        return user

    request.auser = auser
    return request


def make_note(user, book, chapter, collection_name, verses_numbers, note_text):
    """Build a stand-in for a Note row. Note itself uses ArrayField, which needs Postgres, so Note.objects is mocked."""
    return SimpleNamespace(
        user=user,
        book=book,
        chapter=chapter,
        collection_name=collection_name,
        verses_numbers=verses_numbers,
        note=note_text,
    )


class FakeNoteQuerySet:
    """Stands in for a Django QuerySet of notes. Supports order_by() and async iteration."""

    def __init__(self, notes):
        self._notes = notes

    def order_by(self, field_name):
        return FakeNoteQuerySet(sorted(self._notes, key=lambda note: getattr(note, field_name)))

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for note in self._notes:
            yield note


async def get_full_view_context(request, all_notes, book, chapter, version):
    """Call full_view with Note.objects returning all_notes, and return the context passed to async_render."""

    def filter_notes(**lookups):
        matching = [
            note for note in all_notes if all(getattr(note, field) == value for field, value in lookups.items())
        ]
        return FakeNoteQuerySet(matching)

    with (
        patch.multiple(
            "frontend.views.main_site",
            BIBLE_DATA_ROOT=bible_globals.BIBLE_DATA_ROOT,
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            VERSION_SELECTION=bible_globals.VERSION_SELECTION,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
            ALL_VERSES=bible_globals.ALL_VERSES,
            create=True,
        ),
        patch("frontend.views.main_site.Note") as mock_note_model,
    ):
        mock_note_model.objects.filter.side_effect = filter_notes
        with patch("frontend.views.main_site.async_render", new_callable=AsyncMock) as mock_render:
            mock_render.return_value = HttpResponse("ok")
            await main_site.full_view(request, book, chapter, version)

    assert mock_render.called, "full_view did not render the page"
    return mock_render.call_args[0][2]


class FailingObject:
    """Create an object that raises an exception on any operation."""

    def __getattr__(self, name):
        raise RuntimeError("Something went wrong")


class TestFullView(SimpleTestCase):
    """Tests for full_view function."""

    # Success tests
    @pytest.mark.asyncio
    async def test_full_view_success_genesis_1(self):
        """Test that full_view succeeds with valid book, chapter, and version for Genesis 1 (very first chapter in the Bible)."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        request_book = "Genesis"
        request_chapter = 1
        request_version = "bsb"
        request.path_info = f"/{request_book}-{request_chapter}-{request_version}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            BIBLE_DATA_ROOT=bible_globals.BIBLE_DATA_ROOT,
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            VERSION_SELECTION=bible_globals.VERSION_SELECTION,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
            ALL_VERSES=bible_globals.ALL_VERSES,
            create=True,
        ):
            # Mock async_render to return a response
            with patch("frontend.views.main_site.async_render", new_callable=AsyncMock) as mock_render:
                mock_render.return_value = HttpResponse("Genesis 1 content")

                # Call full_view with valid inputs
                response = await main_site.full_view(request, request_book, request_chapter, request_version)

                # Verify async_render was called
                assert mock_render.called
                # Verify we got the correct response back
                assert response is not None
                assert response.content == b"Genesis 1 content"

                # Verify the context passed to async_render
                call_args = mock_render.call_args
                assert call_args is not None

                # verify the request path info is passed to the context (first positional argument)
                assert call_args[0][0].path_info == f"/{request_book}-{request_chapter}-{request_version}/"

                # verify the template name is passed to the context (second positional argument)
                assert call_args[0][1] == "index.html"

                # verify the context is passed to the context (third positional argument)
                context = call_args[0][2]

                # Verify context contains expected book/chapter/version info
                assert context["book"] == request_book
                assert context["chapter"] == request_chapter
                assert context["version"] == request_version
                assert "verses" in context
                assert context["verses"] is not None
                assert len(context["verses"]) > 0

                # Verify navigation context
                assert "previous_book" in context
                assert context["previous_book"] == "Revelation"
                assert "previous_chapter" in context
                assert context["previous_chapter"] == 22
                assert "next_book" in context
                assert context["next_book"] == "Genesis"
                assert "next_chapter" in context
                assert context["next_chapter"] == 2

                # Verify all books, chapters, and versions information
                assert "in_order" in context
                assert context["in_order"] == bible_globals.IN_ORDER_BOOKS
                assert "chapter_selection" in context
                assert context["chapter_selection"] == bible_globals.CHAPTER_SELECTION
                assert "version_selection" in context
                assert context["version_selection"] == bible_globals.VERSION_SELECTION

                # Verify current URL for navigation state
                assert "current_url" in context
                assert context["current_url"] == f"/{request_book}-{request_chapter}-{request_version}/"

    @pytest.mark.asyncio
    async def test_full_view_success_revelation_22(self):
        """Test that full_view succeeds with valid book, chapter, and version for Revelation 22 (very last chapter in the Bible)."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        request_book = "Revelation"
        request_chapter = 22
        request_version = "bsb"
        request.path_info = f"/{request_book}-{request_chapter}-{request_version}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            BIBLE_DATA_ROOT=bible_globals.BIBLE_DATA_ROOT,
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            VERSION_SELECTION=bible_globals.VERSION_SELECTION,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
            ALL_VERSES=bible_globals.ALL_VERSES,
            create=True,
        ):
            # Mock async_render to return a response
            with patch("frontend.views.main_site.async_render", new_callable=AsyncMock) as mock_render:
                mock_render.return_value = HttpResponse("Revelation 22 content")

                # Call full_view with valid inputs
                response = await main_site.full_view(request, request_book, request_chapter, request_version)

                # Verify async_render was called
                assert mock_render.called
                # Verify we got the correct response back
                assert response is not None
                assert response.content == b"Revelation 22 content"

                # Verify the context passed to async_render
                call_args = mock_render.call_args
                assert call_args is not None

                # verify the request path info is passed to the context (first positional argument)
                assert call_args[0][0].path_info == f"/{request_book}-{request_chapter}-{request_version}/"

                # verify the template name is passed to the context (second positional argument)
                assert call_args[0][1] == "index.html"

                # verify the context is passed to the context (third positional argument)
                context = call_args[0][2]

                # Verify context contains expected book/chapter/version info
                assert context["book"] == request_book
                assert context["chapter"] == request_chapter
                assert context["version"] == request_version
                assert "verses" in context
                assert context["verses"] is not None
                assert len(context["verses"]) > 0

                # Verify navigation context
                assert "previous_book" in context
                assert context["previous_book"] == "Revelation"
                assert "previous_chapter" in context
                assert context["previous_chapter"] == 21
                assert "next_book" in context
                assert context["next_book"] == "Genesis"
                assert "next_chapter" in context
                assert context["next_chapter"] == 1

                # Verify all books, chapters, and versions information
                assert "in_order" in context
                assert context["in_order"] == bible_globals.IN_ORDER_BOOKS
                assert "chapter_selection" in context
                assert context["chapter_selection"] == bible_globals.CHAPTER_SELECTION
                assert "version_selection" in context
                assert context["version_selection"] == bible_globals.VERSION_SELECTION

                # Verify current URL for navigation state
                assert "current_url" in context
                assert context["current_url"] == f"/{request_book}-{request_chapter}-{request_version}/"

    @pytest.mark.asyncio
    async def test_full_view_success_2_timothy_2(self):
        """Test that full_view succeeds with valid book, chapter, and version for 2 Timothy 2 (a multi-word chapter name while also checking a mid-chapter and not an edge chapter)."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        request_book = "2 Timothy"
        request_chapter = 2
        request_version = "bsb"
        request.path_info = f"/{request_book}-{request_chapter}-{request_version}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            BIBLE_DATA_ROOT=bible_globals.BIBLE_DATA_ROOT,
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            VERSION_SELECTION=bible_globals.VERSION_SELECTION,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
            ALL_VERSES=bible_globals.ALL_VERSES,
            create=True,
        ):
            # Mock async_render to return a response
            with patch("frontend.views.main_site.async_render", new_callable=AsyncMock) as mock_render:
                mock_render.return_value = HttpResponse("2 Timothy 2 content")

                # Call full_view with valid inputs
                response = await main_site.full_view(request, request_book, request_chapter, request_version)

                # Verify async_render was called
                assert mock_render.called
                # Verify we got the correct response back
                assert response is not None
                assert response.content == b"2 Timothy 2 content"

                # Verify the context passed to async_render
                call_args = mock_render.call_args
                assert call_args is not None

                # verify the request path info is passed to the context (first positional argument)
                assert call_args[0][0].path_info == f"/{request_book}-{request_chapter}-{request_version}/"

                # verify the template name is passed to the context (second positional argument)
                assert call_args[0][1] == "index.html"

                # verify the context is passed to the context (third positional argument)
                context = call_args[0][2]

                # Verify context contains expected book/chapter/version info
                assert context["book"] == request_book
                assert context["chapter"] == request_chapter
                assert context["version"] == request_version
                assert "verses" in context
                assert context["verses"] is not None
                assert len(context["verses"]) > 0

                # Verify navigation context
                assert "previous_book" in context
                assert context["previous_book"] == "2 Timothy"
                assert "previous_chapter" in context
                assert context["previous_chapter"] == 1
                assert "next_book" in context
                assert context["next_book"] == "2 Timothy"
                assert "next_chapter" in context
                assert context["next_chapter"] == 3

                # Verify all books, chapters, and versions information
                assert "in_order" in context
                assert context["in_order"] == bible_globals.IN_ORDER_BOOKS
                assert "chapter_selection" in context
                assert context["chapter_selection"] == bible_globals.CHAPTER_SELECTION
                assert "version_selection" in context
                assert context["version_selection"] == bible_globals.VERSION_SELECTION

                # Verify current URL for navigation state
                assert "current_url" in context
                assert context["current_url"] == f"/{request_book}-{request_chapter}-{request_version}/"

    # Error tests
    @pytest.mark.asyncio
    async def test_full_view_invalid_book(self):
        """Test that full_view redirects with invalid book."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        # We want to intend Revelation 22 WEB because we need a book, chapter, and version that is not the same as the default book, chapter, and version
        request_book = "Invalid"
        request_chapter = 22
        request_version = "web"
        request.path_info = f"/{request_book}-{request_chapter}-{request_version}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            BIBLE_DATA_ROOT=bible_globals.BIBLE_DATA_ROOT,
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            VERSION_SELECTION=bible_globals.VERSION_SELECTION,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
            ALL_VERSES=bible_globals.ALL_VERSES,
            create=True,
        ):
            # Mock async_redirect to return a response
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call full_view with invalid book
                response = await main_site.full_view(request, request_book, request_chapter, request_version)

                # Verify async_redirect was called (since book is invalid)
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to the default book/chapter/version
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are valid defaults
                redirect_args = call_args[1]["args"]
                default_book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert default_book in bible_globals.IN_ORDER_BOOKS
                assert default_book == bible_globals.DEFAULT_BOOK

                # Verify the chapter is valid for that book
                assert default_chapter in range(1, bible_globals.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == bible_globals.DEFAULT_CHAPTER

                # Verify the version is in VERSION_SELECTION
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_full_view_invalid_chapter(self):
        """Test that full_view redirects with invalid chapter."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        # We want to intend Revelation 22 WEB because we need a book, chapter, and version that is not the same as the default book, chapter, and version
        request_book = "Revelation"
        request_chapter = 999
        request_version = "web"
        request.path_info = f"/{request_book}-{request_chapter}-{request_version}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            BIBLE_DATA_ROOT=bible_globals.BIBLE_DATA_ROOT,
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            VERSION_SELECTION=bible_globals.VERSION_SELECTION,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
            ALL_VERSES=bible_globals.ALL_VERSES,
            create=True,
        ):
            # Mock async_redirect to return a response
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call full_view with invalid chapter
                response = await main_site.full_view(request, request_book, request_chapter, request_version)

                # Verify async_redirect was called (since chapter is invalid)
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to the default book/chapter/version
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are valid defaults
                redirect_args = call_args[1]["args"]
                book, chapter, default_version = redirect_args

                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert book in bible_globals.IN_ORDER_BOOKS
                assert book == request_book

                # Verify the chapter is valid for that book
                assert chapter in range(1, bible_globals.CHAPTER_SELECTION[book] + 1)
                assert chapter == 1

                # Verify the version is in VERSION_SELECTION
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_full_view_chapter_is_string(self):
        """Test that full_view redirects with chapter is a string."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        # We want to intend Revelation 22 WEB because we need a book, chapter, and version that is not the same as the default book, chapter, and version
        request_book = "Revelation"
        request_chapter = "Invalid"
        request_version = "web"
        request.path_info = f"/{request_book}-{request_chapter}-{request_version}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            BIBLE_DATA_ROOT=bible_globals.BIBLE_DATA_ROOT,
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            VERSION_SELECTION=bible_globals.VERSION_SELECTION,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
            ALL_VERSES=bible_globals.ALL_VERSES,
            create=True,
        ):
            # Mock async_redirect to return a response
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call full_view with invalid chapter
                response = await main_site.full_view(request, request_book, request_chapter, request_version)

                # Verify async_redirect was called (since chapter is invalid)
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to the default book/chapter/version
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are valid defaults
                redirect_args = call_args[1]["args"]
                book, chapter, default_version = redirect_args

                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert book in bible_globals.IN_ORDER_BOOKS
                assert book == request_book

                # Verify the chapter is valid for that book
                assert chapter in range(1, bible_globals.CHAPTER_SELECTION[book] + 1)
                assert chapter == 1

                # Verify the version is in VERSION_SELECTION
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_full_view_invalid_version(self):
        """Test that full_view redirects with invalid version."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        # We want to intend Revelation 22 WEB because we need a book, chapter, and version that is not the same as the default book, chapter, and version
        request_book = "Revelation"
        request_chapter = 22
        request_version = "Invalid"
        request.path_info = f"/{request_book}-{request_chapter}-{request_version}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            BIBLE_DATA_ROOT=bible_globals.BIBLE_DATA_ROOT,
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            VERSION_SELECTION=bible_globals.VERSION_SELECTION,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
            ALL_VERSES=bible_globals.ALL_VERSES,
            create=True,
        ):
            # Mock async_redirect to return a response
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call full_view with invalid version
                response = await main_site.full_view(request, request_book, request_chapter, request_version)

                # Verify async_redirect was called (since version is invalid)
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to the default book/chapter/version
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are valid defaults
                redirect_args = call_args[1]["args"]
                book, chapter, default_version = redirect_args

                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert book in bible_globals.IN_ORDER_BOOKS
                assert book == request_book

                # Verify the chapter is valid for that book
                assert chapter in range(1, bible_globals.CHAPTER_SELECTION[book] + 1)
                assert chapter == request_chapter

                # Verify the version is in VERSION_SELECTION
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_full_view_general_error(self):
        """Test that full_view handles a general error gracefully."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        # We want to intend Revelation 22 WEB because we need a book, chapter, and version that is not the same as the default book, chapter, and version
        request_book = "Revelation"
        request_chapter = 22
        request_version = "web"
        request.path_info = f"/{request_book}-{request_chapter}-{request_version}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            BIBLE_DATA_ROOT=bible_globals.BIBLE_DATA_ROOT,
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            VERSION_SELECTION=bible_globals.VERSION_SELECTION,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
            ALL_VERSES=FailingObject(),
            create=True,
        ):
            # Mock async_redirect to verify it's called
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call full_view with valid parameters but ALL_VERSES will raise an exception
                response = await main_site.full_view(request, request_book, request_chapter, request_version)

                # Verify async_redirect was called (since an exception occurred)
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to the default book/chapter/version
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are valid defaults
                redirect_args = call_args[1]["args"]
                default_book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert default_book in bible_globals.IN_ORDER_BOOKS
                assert default_book == bible_globals.DEFAULT_BOOK

                # Verify the chapter is valid for that book
                assert default_chapter in range(1, bible_globals.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == bible_globals.DEFAULT_CHAPTER

                # Verify the version is in VERSION_SELECTION
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_full_view_notes_only_include_this_users_notes_for_this_book_chapter_and_version(self):
        """Only the signed-in user's notes for the requested book, chapter, and version are loaded."""
        reset_globals("[]", "bsb", "Genesis", "1")
        user = SimpleNamespace(username="notes-view-user", is_authenticated=True)
        other_user = SimpleNamespace(username="other-notes-user", is_authenticated=True)
        all_notes = [
            make_note(user, "Genesis", 1, "bsb", [16], "sixteen"),
            make_note(user, "Genesis", 1, "bsb", [2], "two"),
            make_note(user, "Genesis", 1, "bsb", [10], "ten"),
            make_note(other_user, "Genesis", 1, "bsb", [1], "other user note"),
            make_note(user, "Genesis", 2, "bsb", [1], "chapter two note"),
            make_note(user, "Genesis", 1, "kjv", [1], "kjv note"),
        ]

        context = await get_full_view_context(add_auser(HttpRequest(), user), all_notes, "Genesis", 1, "bsb")

        assert {note.decrypted_note for note in context["notes"]} == {"sixteen", "two", "ten"}

    @pytest.mark.asyncio
    async def test_full_view_notes_are_ordered_by_verse_numbers(self):
        """Notes are sorted by verse, not by the order they were created."""
        reset_globals("[]", "bsb", "Genesis", "1")
        user = SimpleNamespace(username="notes-view-user", is_authenticated=True)
        all_notes = [
            make_note(user, "Genesis", 1, "bsb", [16], "sixteen"),
            make_note(user, "Genesis", 1, "bsb", [2], "two"),
            make_note(user, "Genesis", 1, "bsb", [10], "ten"),
        ]

        context = await get_full_view_context(add_auser(HttpRequest(), user), all_notes, "Genesis", 1, "bsb")

        assert [note.decrypted_note for note in context["notes"]] == ["two", "ten", "sixteen"]

    @pytest.mark.asyncio
    async def test_full_view_anonymous_user_gets_no_notes(self):
        """A signed-out visitor gets an empty notes list, even when notes exist for the chapter."""
        reset_globals("[]", "bsb", "Genesis", "1")
        user = SimpleNamespace(username="notes-view-user")
        all_notes = [make_note(user, "Genesis", 1, "bsb", [1], "private note")]

        context = await get_full_view_context(add_auser(HttpRequest()), all_notes, "Genesis", 1, "bsb")

        assert context["notes"] == []


class TestBookChapterView(SimpleTestCase):
    """Tests for book_chapter_view function."""

    # Success tests
    @pytest.mark.asyncio
    async def test_book_chapter_view_success_genesis_1(self):
        """Test that book_chapter_view redirects to full_view with default version for Genesis 1 (first chapter in the Bible)."""
        reset_globals("[]", "bsb", "Genesis", "1")

        request = add_auser(HttpRequest())
        request_book = "Genesis"
        request_chapter = 1
        request.path_info = f"/{request_book}-{request_chapter}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
        ):
            # Mock async_redirect to verify it's called
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call book_chapter_view with valid book and chapter
                response = await main_site.book_chapter_view(request, request_book, request_chapter)

                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to full_view with the default version
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args include the book, chapter, and default version
                redirect_args = call_args[1]["args"]
                book, chapter, default_version = redirect_args

                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert book in bible_globals.IN_ORDER_BOOKS
                assert book == request_book

                # Verify the chapter is valid for that book
                assert chapter in range(1, bible_globals.CHAPTER_SELECTION[book] + 1)
                assert chapter == request_chapter

                # Verify the version is the default version
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_book_chapter_view_success_revelation_22(self):
        """Test that book_chapter_view redirects to full_view with default version for Revelation 22 (very last chapter in the Bible)."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        request_book = "Revelation"
        request_chapter = 22
        request.path_info = f"/{request_book}-{request_chapter}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
        ):
            # Mock async_redirect to verify it's called
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call book_chapter_view with valid book and chapter
                response = await main_site.book_chapter_view(request, request_book, request_chapter)

                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to full_view with the default version
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args include the book, chapter, and default version
                redirect_args = call_args[1]["args"]
                book, chapter, default_version = redirect_args

                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert book in bible_globals.IN_ORDER_BOOKS
                assert book == request_book

                # Verify the chapter is valid for that book
                assert chapter in range(1, bible_globals.CHAPTER_SELECTION[book] + 1)
                assert chapter == request_chapter

                # Verify the version is the default version
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_book_chapter_view_success_2_timothy_2(self):
        """Test that book_chapter_view redirects to full_view with default version for 2 Timothy 2 (a multi-word chapter name while also checking a mid-chapter and not an edge chapter)."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        request_book = "2 Timothy"
        request_chapter = 2
        request.path_info = f"/{request_book}-{request_chapter}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
            create=True,
        ):
            # Mock async_redirect to verify it's called
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call book_chapter_view with valid book and chapter
                response = await main_site.book_chapter_view(request, request_book, request_chapter)

                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to full_view with the default version
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args include the book, chapter, and default version
                redirect_args = call_args[1]["args"]
                book, chapter, default_version = redirect_args

                # Verify the redirect goes to a valid book that exists in IN_ORDER_BOOKS
                assert book in bible_globals.IN_ORDER_BOOKS
                assert book == request_book

                # Verify the chapter is valid for that book
                assert chapter in range(1, bible_globals.CHAPTER_SELECTION[book] + 1)
                assert chapter == request_chapter

                # Verify the version is the default version
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_book_chapter_view_invalid_book(self):
        """Test that book_chapter_view redirects to defaults when given invalid book."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        # We want to intend Revelation 22 because we need a book and chapter that is not the same as the default book and chapter
        request_book = "Invalid"
        request_chapter = 22
        request.path_info = f"/{request_book}-{request_chapter}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
        ):
            # Mock async_redirect to verify it's called
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call book_chapter_view with invalid book
                response = await main_site.book_chapter_view(request, request_book, request_chapter)

                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to full_view with defaults
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are all defaults
                redirect_args = call_args[1]["args"]
                default_book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert default_book in bible_globals.IN_ORDER_BOOKS
                assert default_book == bible_globals.DEFAULT_BOOK

                # Verify the chapter is the default chapter
                assert default_chapter in range(1, bible_globals.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == bible_globals.DEFAULT_CHAPTER

                # Verify the version is the default version
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_book_chapter_view_invalid_chapter(self):
        """Test that book_chapter_view redirects to default chapter when given invalid chapter."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        # We want to intend Revelation 22 because we need a book and chapter that is not the same as the default book and chapter
        request_book = "Revelation"
        request_chapter = 999
        request.path_info = f"/{request_book}-{request_chapter}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
        ):
            # Mock async_redirect to verify it's called
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call book_chapter_view with invalid chapter
                response = await main_site.book_chapter_view(request, request_book, request_chapter)

                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to full_view with default chapter and version
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are book, default chapter, and default version
                redirect_args = call_args[1]["args"]
                book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert book in bible_globals.IN_ORDER_BOOKS
                assert book == request_book

                # Verify the chapter is the default chapter
                assert default_chapter in range(1, bible_globals.CHAPTER_SELECTION[book] + 1)
                assert default_chapter == 1

                # Verify the version is the default version
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_book_chapter_view_chapter_is_string(self):
        """Test that book_chapter_view redirects to default chapter when given invalid chapter."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        # We want to intend Revelation 22 because we need a book and chapter that is not the same as the default book and chapter
        request_book = "Revelation"
        request_chapter = "Invalid"
        request.path_info = f"/{request_book}-{request_chapter}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
        ):
            # Mock async_redirect to verify it's called
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call book_chapter_view with invalid chapter
                response = await main_site.book_chapter_view(request, request_book, request_chapter)

                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to full_view with default chapter and version
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are book, default chapter, and default version
                redirect_args = call_args[1]["args"]
                book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert book in bible_globals.IN_ORDER_BOOKS
                assert book == request_book

                # Verify the chapter is the default chapter
                assert default_chapter in range(1, bible_globals.CHAPTER_SELECTION[book] + 1)
                assert default_chapter == 1

                # Verify the version is the default version
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_book_chapter_view_general_error(self):
        """Test that book_chapter_view handles errors gracefully."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        # We want to intend Revelation 22 because we need a book and chapter that is not the same as the default book and chapter
        request_book = "Revelation"
        request_chapter = 22
        request.path_info = f"/{request_book}-{request_chapter}/"

        # Patch the globals in views module with IN_ORDER_BOOKS that will cause an error
        with patch.multiple(
            "frontend.views.main_site",
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            IN_ORDER_BOOKS=FailingObject(),
            CHAPTER_SELECTION=bible_globals.CHAPTER_SELECTION,
        ):
            # Mock async_redirect to verify it's called
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call book_chapter_view - the FailingObject will cause an exception
                response = await main_site.book_chapter_view(request, request_book, request_chapter)

                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None

                # Verify the redirect was to full_view with defaults
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are all defaults
                redirect_args = call_args[1]["args"]
                default_book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert default_book in bible_globals.IN_ORDER_BOOKS
                assert default_book == bible_globals.DEFAULT_BOOK

                # Verify the chapter is the default chapter
                assert default_chapter in range(1, bible_globals.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == 1

                # Verify the version is the default version
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION


class TestBookView(SimpleTestCase):
    """Tests for book_view function."""

    # Success tests
    @pytest.mark.asyncio
    async def test_book_view_success_genesis(self):
        """Test that book_view redirects to full_view with chapter 1 and default version for Genesis (first book in the Bible)."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        request_book = "Genesis"
        request.path_info = f"/{request_book}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
        ):
            # Mock async_redirect to verify it's called
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call book_view with valid book
                response = await main_site.book_view(request, request_book)

                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to full_view with the specified book, chapter 1, and default version
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are the specified book, chapter 1, and default version
                redirect_args = call_args[1]["args"]
                book, chapter, default_version = redirect_args

                # Verify the redirect goes to the specified book
                assert book in bible_globals.IN_ORDER_BOOKS
                assert book == request_book

                # Verify the chapter is the specified chapter
                assert chapter in range(1, bible_globals.CHAPTER_SELECTION[book] + 1)
                assert chapter == 1

                # Verify the version is the default version
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_book_view_success_revelation(self):
        """Test that book_view redirects to full_view with chapter 1 and default version for Revelation (last book in the Bible)."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        request_book = "Revelation"
        request.path_info = f"/{request_book}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
        ):
            # Mock async_redirect to verify it's called
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call book_view with valid book
                response = await main_site.book_view(request, request_book)

                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to full_view with the specified book, chapter 1, and default version
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are the specified book, chapter 1, and default version
                redirect_args = call_args[1]["args"]
                book, chapter, default_version = redirect_args

                # Verify the redirect goes to the specified book
                assert book in bible_globals.IN_ORDER_BOOKS
                assert book == request_book

                # Verify the chapter is the specified chapter
                assert chapter in range(1, bible_globals.CHAPTER_SELECTION[book] + 1)
                assert chapter == 1

                # Verify the version is the default version
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_book_view_success_2_timothy(self):
        """Test that book_view redirects to full_view with chapter 1 and default version."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        request_book = "2 Timothy"
        request.path_info = f"/{request_book}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
        ):
            # Mock async_redirect to verify it's called
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call book_view with valid book
                response = await main_site.book_view(request, request_book)

                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to full_view with the specified book, chapter 1, and default version
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are the specified book, chapter 1, and default version
                redirect_args = call_args[1]["args"]
                book, chapter, default_version = redirect_args

                # Verify the redirect goes to the specified book
                assert book in bible_globals.IN_ORDER_BOOKS
                assert book == request_book

                # Verify the chapter is the specified chapter
                assert chapter in range(1, bible_globals.CHAPTER_SELECTION[book] + 1)
                assert chapter == 1

                # Verify the version is the default version
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    # Error tests
    @pytest.mark.asyncio
    async def test_book_view_invalid_book(self):
        """Test that book_view redirects to defaults when given invalid book."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        # We want to intend Revelation because we need a book that is not the same as the default book
        request_book = "Invalid"
        request.path_info = f"/{request_book}/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            IN_ORDER_BOOKS=bible_globals.IN_ORDER_BOOKS,
        ):
            # Mock async_redirect to verify it's called
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call book_view with invalid book
                response = await main_site.book_view(request, request_book)

                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to full_view with defaults
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are the default book, default chapter, and default version
                redirect_args = call_args[1]["args"]
                default_book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert default_book in bible_globals.IN_ORDER_BOOKS
                assert default_book == bible_globals.DEFAULT_BOOK

                # Verify the chapter is the default chapter
                assert default_chapter in range(1, bible_globals.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == bible_globals.DEFAULT_CHAPTER

                # Verify the version is the default version
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    @pytest.mark.asyncio
    async def test_book_view_general_error(self):
        """Test that book_view handles errors gracefully."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())

        # We want to intend Revelation because we need a book that is not the same as the default book
        request_book = "Revelation"
        request.path_info = f"/{request_book}/"

        # Patch the globals in views module with IN_ORDER_BOOKS that will cause an error
        with patch.multiple(
            "frontend.views.main_site",
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            IN_ORDER_BOOKS=FailingObject(),
        ):
            # Mock async_redirect to verify it's called
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call book_view - the FailingObject will cause an exception
                response = await main_site.book_view(request, request_book)

                # Verify async_redirect was called (due to the exception)
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to full_view with defaults
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are the default book, default chapter, and default version
                redirect_args = call_args[1]["args"]
                default_book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert default_book in bible_globals.IN_ORDER_BOOKS
                assert default_book == bible_globals.DEFAULT_BOOK

                # Verify the chapter is the default chapter
                assert default_chapter in range(1, bible_globals.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == bible_globals.DEFAULT_CHAPTER

                # Verify the version is the default version
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION


class TestDefaultView(SimpleTestCase):
    """Tests for default_view function."""

    # Success tests
    @pytest.mark.asyncio
    async def test_default_view_success(self):
        """Test that default_view redirects to full_view with default book, chapter, and version."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())
        request.path_info = "/"

        # Patch the globals in views module to match what we set up
        with patch.multiple(
            "frontend.views.main_site",
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
        ):
            # Mock async_redirect to verify it's called
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call default_view
                response = await main_site.default_view(request)

                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to full_view with defaults
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are the default book, default chapter, and default version
                redirect_args = call_args[1]["args"]
                default_book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert default_book in bible_globals.IN_ORDER_BOOKS
                assert default_book == bible_globals.DEFAULT_BOOK

                # Verify the chapter is the default chapter
                assert default_chapter in range(1, bible_globals.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == bible_globals.DEFAULT_CHAPTER

                # Verify the version is the default version
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION

    # Error tests
    @pytest.mark.asyncio
    async def test_default_view_general_error(self):
        """Test that default_view handles errors gracefully."""
        reset_globals("[]", "bsb", "Genesis", "1")
        request = add_auser(HttpRequest())
        request.path_info = "/"

        # Patch the globals in views module with VERSION_SELECTION that will cause an error
        with patch.multiple(
            "frontend.views.main_site",
            DEFAULT_VERSION=bible_globals.DEFAULT_VERSION,
            DEFAULT_BOOK=bible_globals.DEFAULT_BOOK,
            DEFAULT_CHAPTER=bible_globals.DEFAULT_CHAPTER,
            VERSION_SELECTION=FailingObject(),
        ):
            # Mock async_redirect to verify it's called
            with patch("frontend.views.main_site.async_redirect", new_callable=AsyncMock) as mock_redirect:
                mock_redirect.return_value = HttpResponse("Redirected")

                # Call default_view - the FailingObject will cause an exception
                response = await main_site.default_view(request)

                # Verify async_redirect was called
                assert mock_redirect.called
                # Verify we got a response
                assert response is not None
                assert response.content == b"Redirected"

                # Verify the redirect was to full_view with defaults
                call_args = mock_redirect.call_args
                assert call_args is not None

                # Verify the view name is 'full_view'
                assert call_args[0][0] == "full_view"

                # Verify the redirect args are the default book, default chapter, and default version
                redirect_args = call_args[1]["args"]
                default_book, default_chapter, default_version = redirect_args

                # Verify the redirect goes to the default book
                assert default_book in bible_globals.IN_ORDER_BOOKS
                assert default_book == bible_globals.DEFAULT_BOOK

                # Verify the chapter is the default chapter
                assert default_chapter in range(1, bible_globals.CHAPTER_SELECTION[default_book] + 1)
                assert default_chapter == bible_globals.DEFAULT_CHAPTER

                # Verify the version is the default version
                assert default_version in bible_globals.VERSION_SELECTION
                assert default_version == bible_globals.DEFAULT_VERSION
