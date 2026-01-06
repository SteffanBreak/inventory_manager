from django.contrib import admin
from .models import Product, Supplier, ConsumptionLog


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "current_stock", "minimum_stock_level")
    search_fields = ("name", "sku")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_email", "lead_time_days")


@admin.register(ConsumptionLog)
class ConsumptionLogAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "date")
    list_filter = ("date", "product")
