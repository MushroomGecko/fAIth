from asgiref.sync import sync_to_async
from django import forms
from django.contrib.auth import aauthenticate, alogin
from django.shortcuts import redirect, render
from ninja import Router

from fAIth.api_tags import APITags

router = Router()


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


@router.get("/login", tags=[APITags.BACKEND], url_name="login")
async def login_page(request):
    """Render the login form."""
    form = await sync_to_async(LoginForm, thread_sensitive=True)()
    return await sync_to_async(render, thread_sensitive=True)(request, "registration/login.html", {"form": form})


@router.post("/login", tags=[APITags.BACKEND])
async def login(request):
    """Authenticate a user and redirect to the main site on success."""
    form = await sync_to_async(LoginForm, thread_sensitive=True)(request.POST)
    is_valid = await sync_to_async(form.is_valid, thread_sensitive=True)()

    user = None
    if is_valid:
        user = await aauthenticate(
            request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )

    if user is not None:
        await alogin(request, user)
        return redirect("/")

    if is_valid:
        form.add_error(
            None,
            "Please enter a correct username and password. Note that both fields may be case-sensitive.",
        )

    return await sync_to_async(render, thread_sensitive=True)(
        request, "registration/login.html", {"form": form}, status=400
    )
