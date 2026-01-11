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
        
        # Scenarios distribution
        scenarios = ["normal"] * 6 + ["critical"] * 2 + ["low"] * 2 # 60% normal, 20% critical, 20% low

        for cat_code, items in categories.items():
            for name in items:
                scenario = random.choice(scenarios)
                
                # Default stock params
                if scenario == "critical":
                    # High consumption will be simulated, stock should be almost out
                    current_stock = random.randint(5, 20)
                    min_stock = random.randint(10, 30)
                elif scenario == "low":
                    # Stock below min, but maybe consumption isn't crazy high
                    min_stock = random.randint(20, 40)
                    current_stock = random.randint(5, min_stock - 1)
                else:
                    # Healthy stock
                    current_stock = random.randint(50, 200)
                    min_stock = random.randint(10, 30)

                p, created = Product.objects.get_or_create(
                    name=name,
                    defaults={
                        "sku": f"SKU-{cat_code}-{name.replace(' ', '')[:4].upper()}-{random.randint(100, 999)}",
                        "current_stock": current_stock,
                        "minimum_stock_level": min_stock,
                    },
                )
                
                # If product already existed, update stock to match scenario for this run
                if not created:
                    p.current_stock = current_stock
                    p.minimum_stock_level = min_stock
                    p.save()

                p.suppliers.set(random.sample(suppliers, k=random.randint(1, 2)))
                products.append(p)

        # Create Consumption Logs (Past 30 days)
        today = timezone.now().date()
        
        # Delete old logs to reset scenarios cleanly
        ConsumptionLog.objects.all().delete()
        
        for p in products:
            # Determine consumption profile based on stock (reverse engineer scenario)
            # If stock is low/critical, we ensure consumption is high enough to trigger alerts
            
            is_critical = p.current_stock < 25 # Heuristic from above
            
            for day in range(30):
                date = today - timedelta(days=day)
                
                # Consumption profile
                params = {
                    "chance": 0.3,
                    "min_q": 1,
                    "max_q": 10
                }
                
                if is_critical:
                    params = {"chance": 0.8, "min_q": 5, "max_q": 15} # Heavy usage
                
                if random.random() < params["chance"]:
                    ConsumptionLog.objects.create(
                        product=p,
                        date=date,
                        quantity=random.randint(params["min_q"], params["max_q"]),
                        notes="Daily usage",
                    )

        self.stdout.write(self.style.SUCCESS("Data seeded successfully"))
