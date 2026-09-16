from django.contrib import admin

from messaging.models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("sender", "body", "read_at", "created_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("public_id", "property", "traveler", "host", "last_message_at")
    search_fields = ("property__title", "traveler__email", "host__email")
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = [MessageInline]
