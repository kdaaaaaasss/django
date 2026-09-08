from django.contrib import admin

from .models import Ticket, TicketMessage


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ('created_at', 'is_staff')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'user', 'category', 'status',
                    'priority', 'assigned_to', 'updated_at')
    list_filter = ('status', 'priority', 'category')
    list_editable = ('status', 'priority', 'assigned_to')
    search_fields = ('subject', 'user__username')
    inlines = (TicketMessageInline,)
