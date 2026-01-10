import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from inventory.models import Product, Supplier, ConsumptionLog


class Command(BaseCommand):
    help = "Seeds the database with initial data"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding data...")

        # Create Suppliers
        suppliers = []
        for i in range(3):
            s, created = Supplier.objects.get_or_create(
                name=f"Supplier {i+1}",
                defaults={
                    "contact_email": f"supplier{i+1}@example.com",
                    "lead_time_days": random.randint(1, 7),
                },
            )
            suppliers.append(s)

        # Create Products
        products = []
        categories = {
            "GRO": ["Avocados", "Olive Oil", "Flour", "Eggs", "Cheese", "Bacon", "Lettuce"],
            "BEV": ["Green Tea", "Black Tea", "Espresso Pods", "Syrup (Vanilla)", "Syrup (Caramel)", "Almond Milk"],
            "SUP": ["Paper Towels", "Trash Bags", "Dish Soap", "Sponges", "Sanitizer", "Straws", "Lids"]
        }
        
        for cat_code, items in categories.items():
            for name in items:
                p, created = Product.objects.get_or_create(
                    name=name,
                    defaults={
                        "sku": f"SKU-{cat_code}-{name.replace(' ', '')[:4].upper()}-{random.randint(100, 999)}",
                        "current_stock": random.randint(10, 150),
                        "minimum_stock_level": random.randint(5, 20),
                    },
                )
                p.suppliers.set(random.sample(suppliers, k=random.randint(1, 2)))
                products.append(p)

        # Create Consumption Logs (Past 30 days)
        today = timezone.now().date()
        for p in products:
            for day in range(30):
                date = today - timedelta(days=day)
                # Random consumption
                if random.random() > 0.3:  # 70% chance of consumption
                    qty = random.randint(1, 10)
                    ConsumptionLog.objects.get_or_create(
                        product=p,
                        date=date,
                        defaults={
                            "quantity": qty,
                            "notes": "Daily usage",
                        },
                    )

        self.stdout.write(self.style.SUCCESS("Data seeded successfully"))
