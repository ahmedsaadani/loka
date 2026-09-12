from django.contrib import admin

from reviews.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("booking", "author", "rating", "is_published", "created_at")
    list_filter = ("rating", "is_published")
