from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models import HostProfile, IdentityDocument, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("-created_at",)
    list_display = ("email", "first_name", "last_name", "role", "is_identity_verified", "is_active")
    list_filter = ("role", "is_identity_verified", "is_active")
    search_fields = ("email", "first_name", "last_name", "phone")
    readonly_fields = ("public_id", "last_login", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("email", "password", "public_id")}),
        ("Profil", {"fields": ("first_name", "last_name", "phone", "preferred_language")}),
        ("Rôle", {"fields": ("role", "is_identity_verified")}),
        ("Accès", {"fields": ("is_active", "is_staff", "is_superuser", "groups")}),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2", "role")}),
    )


@admin.register(HostProfile)
class HostProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "company_name", "bank_details_masked")
    search_fields = ("display_name", "user__email", "company_name")
    # L'IBAN complet n'est pas affiché dans l'admin.
    exclude = ("bank_iban_private",)
    readonly_fields = ("bank_details_masked",)


@admin.register(IdentityDocument)
class IdentityDocumentAdmin(admin.ModelAdmin):
    list_display = ("user", "doc_type", "status", "created_at", "reviewed_by", "reviewed_at")
    list_filter = ("status", "doc_type")
    search_fields = ("user__email",)
    # Statut modifié uniquement via les services (ADR 0003) ; fichier jamais lié depuis l'admin.
    readonly_fields = ("public_id", "status", "file", "mime_type", "reviewed_by", "reviewed_at")
