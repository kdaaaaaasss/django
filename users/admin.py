from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль'
    fields = ('role', 'phone', 'created_at')
    readonly_fields = ('created_at',)


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'get_role', 'is_staff', 'date_joined')
    list_select_related = ('profile',)

    @admin.display(description='Роль')
    def get_role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, 'profile') else '—'


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'created_at')
    list_filter = ('role',)
    list_editable = ('role',)
    search_fields = ('user__username', 'user__email', 'phone')
