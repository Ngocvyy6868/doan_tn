from django.contrib import admin

from .models import Address, Category, Customer, Product, ProductAttribute


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'created_at')
    search_fields = ('full_name', 'phone', 'user__email')

    @admin.display(ordering='user__email')
    def email(self, customer):
        return customer.user.email


admin.site.register(Address)
admin.site.register(Category)
admin.site.register(ProductAttribute)
admin.site.register(Product)
