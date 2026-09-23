from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'created_at')
    search_fields = ('full_name', 'phone', 'user__email')

    @admin.display(ordering='user__email')
    def email(self, customer):
        return customer.user.email
