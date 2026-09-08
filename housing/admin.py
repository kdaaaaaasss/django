from django.contrib import admin
from django.utils.html import format_html

from .models import Amenity, Booking, Housing, HousingImage


class HousingImageInline(admin.TabularInline):
    model = HousingImage
    extra = 1


@admin.register(Housing)
class HousingAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status_badge', 'deal_type', 'price',
                    'rooms', 'rating', 'is_featured', 'created_at')
    list_editable = ('is_featured',)
    list_filter = ('status', 'is_featured', 'deal_type', 'housing_type', 'rooms')
    search_fields = ('title', 'address', 'description', 'owner__username')
    autocomplete_fields = ('owner',)
    filter_horizontal = ('amenities',)
    inlines = (HousingImageInline,)
    readonly_fields = ('rating', 'reviews_count', 'views_count',
                       'moderated_by', 'moderated_at', 'created_at', 'updated_at')
    actions = ('action_approve', 'action_reject', 'action_feature')
    fieldsets = (
        (None, {'fields': ('owner', 'title', 'slug', 'short_description', 'description')}),
        ('Адрес', {'fields': ('city', 'address')}),
        ('Параметры', {'fields': ('housing_type', 'deal_type', 'price', 'rooms',
                                  'guests', 'area', 'amenities', 'image')}),
        ('Модерация', {'fields': ('status', 'rejection_reason', 'is_featured',
                                  'moderated_by', 'moderated_at')}),
        ('Статистика', {'fields': ('rating', 'reviews_count', 'views_count',
                                   'created_at', 'updated_at')}),
    )

    @admin.display(description='Статус')
    def status_badge(self, obj):
        colors = {'draft': '#888', 'pending': '#9a6700',
                  'approved': '#1a7f37', 'rejected': '#c02b45'}
        return format_html('<b style="color:{}">{}</b>',
                           colors.get(obj.status, '#000'), obj.get_status_display())

    @admin.action(description='Одобрить выбранные')
    def action_approve(self, request, queryset):
        for obj in queryset:
            obj.approve(by=request.user)
        self.message_user(request, f'Одобрено: {queryset.count()}')

    @admin.action(description='Отклонить выбранные')
    def action_reject(self, request, queryset):
        for obj in queryset:
            obj.reject('Отклонено массовым действием в админке', by=request.user)
        self.message_user(request, f'Отклонено: {queryset.count()}')

    @admin.action(description='Переключить «на главной»')
    def action_feature(self, request, queryset):
        for obj in queryset:
            obj.is_featured = not obj.is_featured
            obj.save(update_fields=['is_featured'])


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'housing', 'guest', 'check_in', 'check_out',
                    'nights', 'total_price', 'status')
    list_filter = ('status', 'check_in')
    search_fields = ('housing__title', 'guest__username')
    autocomplete_fields = ('housing', 'guest')
    readonly_fields = ('created_at', 'decided_at', 'decided_by')


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'icon', 'order')
    search_fields = ('name', 'code')


admin.site.register(HousingImage)

admin.site.site_header = 'Рязань.Аренда — администрирование'
admin.site.site_title = 'Рязань.Аренда'
admin.site.index_title = 'Управление сайтом'
