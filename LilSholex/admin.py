from django.contrib import admin


class BUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat_id', 'rank', 'status', 'menu_mode', 'last_usage_date', 'registration_date')
    list_filter = ('rank', 'status', 'menu_mode')
    date_hierarchy = 'registration_date'
    list_per_page = 15
    search_fields = ('id', 'chat_id')
    readonly_fields = ('id', 'registration_date', 'last_usage_date')
