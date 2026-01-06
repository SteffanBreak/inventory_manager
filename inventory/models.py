from django.db import models


class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    lead_time_days = models.PositiveIntegerField(
        help_text="Average delivery time in days"
    )

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50, unique=True)
    current_stock = models.PositiveIntegerField(default=0)
    minimum_stock_level = models.PositiveIntegerField(default=10)
    suppliers = models.ManyToManyField(Supplier, related_name="products")

    def __str__(self):
        return f"{self.name} ({self.sku})"


class ConsumptionLog(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="consumption_logs"
    )
    quantity = models.PositiveIntegerField()
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} on {self.date}"
