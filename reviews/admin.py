from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('housing', 'author', 'rating', 'status', 'created_at')
    list_filter = ('status', 'rating')
    search_fields = ('housing__title', 'author__username', 'text')
    readonly_fields = ('created_at', 'replied_at')
    actions = ('action_publish', 'action_reject')

    @admin.action(description='Опубликовать')
    def action_publish(self, request, queryset):
        for r in queryset:
            r.publish(by=request.user)

    @admin.action(description='Отклонить')
    def action_reject(self, request, queryset):
        for r in queryset:
            r.reject(by=request.user)
