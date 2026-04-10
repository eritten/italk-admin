from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import Domain, EmailOTP, Extension, Session, User

admin.site.site_header = "iTalkVoIP Admin"
admin.site.site_title = "iTalkVoIP Admin"
admin.site.index_title = "iTalkVoIP Admin"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    ordering = ("-created_at",)
    list_display = ("email", "role", "is_verified", "selected_domain", "is_staff", "created_at")
    list_filter = ("role", "is_verified", "is_staff", "is_superuser", "is_active")
    search_fields = ("email",)
    readonly_fields = ("created_at", "updated_at", "last_login")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Access", {"fields": ("role", "is_verified", "selected_domain")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "role", "is_verified", "is_staff", "is_superuser"),
            },
        ),
    )


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("identifier", "label", "is_active", "extension_start", "created_at")
    list_filter = ("is_active",)
    search_fields = ("identifier", "label")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Extension)
class ExtensionAdmin(admin.ModelAdmin):
    list_display = ("user", "domain", "extension_number", "created_at")
    search_fields = ("user__email", "domain__identifier", "domain__label")
    readonly_fields = ("created_at", "updated_at")


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "code", "expires_at", "consumed_at", "created_at")
    list_filter = ("purpose", "consumed_at")
    search_fields = ("user__email", "code")
    readonly_fields = ("created_at",)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("user", "expires_at", "revoked_at", "ip_address", "created_at")
    list_filter = ("revoked_at",)
    search_fields = ("user__email", "ip_address", "user_agent")
    readonly_fields = ("created_at", "updated_at")
