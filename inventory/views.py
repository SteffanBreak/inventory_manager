import io
import urllib
import base64
import pandas as pd
import matplotlib.pyplot as plt
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone
from .models import Product, ConsumptionLog
from .forms import ProductForm


class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = "inventory/product_form.html"
    success_url = reverse_lazy("product_list")


class ProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "inventory/product_form.html"
    success_url = reverse_lazy("product_list")


class ProductListView(ListView):
    model = Product
    template_name = "inventory/product_list.html"
    context_object_name = "products"


class ProductDetailView(DetailView):
    model = Product
    template_name = "inventory/product_detail.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        logs = product.consumption_logs.all().order_by("date")

        if logs.exists():
            # Data preparation
            data = {
                "date": [log.date for log in logs],
                "quantity": [log.quantity for log in logs],
            }
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            df.set_index("date", inplace=True)
            
            # Resample to daily frequency
            # TODO: Fix gap filling later
            daily_df = df.resample('D').sum()

            # Calculate average daily consumption (last 30 days or all)
            avg_daily_usage = daily_df["quantity"].mean()

            # Prediction
            # Potential division by zero here if usage is 0
            if avg_daily_usage != 0:
                days_left = product.current_stock / avg_daily_usage
                prediction_date = timezone.now().date() + timezone.timedelta(days=days_left)
                context["prediction_date"] = prediction_date
                context["days_remaining"] = int(days_left)

            # Graph generation
            plt.figure(figsize=(10, 5))
            plt.plot(daily_df.index, daily_df["quantity"], marker='o', linestyle='-')
            plt.title('Daily Consumption Trend')
            plt.xlabel('Date')
            plt.ylabel('Quantity')
            plt.grid(True)
            plt.tight_layout()

            # Save graph to memory
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            string = base64.b64encode(buf.read())
            uri = urllib.parse.quote(string)
            context["graph"] = uri
            plt.close()

        return context
