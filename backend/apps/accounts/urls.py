from django.urls import path

from . import views

app_name = "accounts"
urlpatterns = [
    path("session/", views.session, name="session"),
    path("login/", views.sign_in, name="login"),
    path("register/", views.sign_up, name="register"),
    path("logout/", views.sign_out, name="logout"),
    path("password/change/", views.change_password, name="password-change"),
    path("password/reset/", views.request_password_reset, name="password-reset"),
    path("password/reset/confirm/", views.confirm_password_reset, name="password-reset-confirm"),
]
