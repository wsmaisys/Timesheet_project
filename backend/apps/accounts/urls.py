from django.urls import path

from .views import (
    CurrentUserView,
    LoginView,
    LogoutView,
    RefreshView,
    UserDetailView,
    UserListCreateView,
)

urlpatterns = [
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/refresh", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("auth/me", CurrentUserView.as_view(), name="auth-me"),
    path("users", UserListCreateView.as_view(), name="user-list-create"),
    path("users/<uuid:user_id>", UserDetailView.as_view(), name="user-detail"),
]
