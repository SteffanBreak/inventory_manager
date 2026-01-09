import io
import urllib
import base64
import numpy as np
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

        # Get trend models from request parameters (default to 'linear')
        consumption_model = self.request.GET.get('consumption_model', 'p1') # p1 for polyfit deg 1
        stock_model = self.request.GET.get('stock_model', 'p1')

        context['consumption_model'] = consumption_model
        context['stock_model'] = stock_model

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
            
            # Resample to daily frequency and fill 0 for missing days
            daily_df = df.resample('D').sum().fillna(0)

            # Calculate average daily consumption
            avg_daily_usage = daily_df["quantity"].mean()

            # Prediction logic
            if avg_daily_usage > 0:
                days_left = product.current_stock / avg_daily_usage
                prediction_date = timezone.now().date() + timezone.timedelta(days=days_left)
                context["prediction_date"] = prediction_date
                context["days_remaining"] = int(days_left)

            def get_trend_poly(x, y, model_code):
                deg = 2 if model_code == 'p2' else 1
                try:
                    z = np.polyfit(x, y, deg)
                    p = np.poly1d(z)
                    y_pred = p(x)
                    rmse = np.sqrt(np.mean((y - y_pred)**2))
                    return p(x), rmse
                except Exception:
                    return None, None

            # --- Graph 1: Consumption ---
            plt.figure(figsize=(10, 5))
            plt.plot(daily_df.index, daily_df["quantity"], marker='o', linestyle='-', label='Consumption')
            
            if len(daily_df) > 1:
                x = np.arange(len(daily_df))
                y = daily_df["quantity"].values
                trend_y, rmse = get_trend_poly(x, y, consumption_model)
                
                if trend_y is not None:
                    label = f'Trend ({consumption_model}, RMSE={rmse:.2f})'
                    plt.plot(daily_df.index, trend_y, "r--", linewidth=2, label=label)
                    context['consumption_rmse'] = round(rmse, 2)

            plt.title('Daily Consumption Trend')
            plt.xlabel('Date')
            plt.ylabel('Quantity')
            plt.legend()
            plt.grid(True)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            string = base64.b64encode(buf.read())
            context["graph"] = urllib.parse.quote(string)
            plt.close()

            # --- Graph 2: Stock Level ---
            total_consumed = daily_df["quantity"].sum()
            simulated_start_stock = product.current_stock + total_consumed
            daily_df["stock_level"] = simulated_start_stock - daily_df["quantity"].cumsum()

            plt.figure(figsize=(10, 5))
            plt.plot(daily_df.index, daily_df["stock_level"], marker='s', linestyle='-', color='green', label='Stock Level')

            if len(daily_df) > 1:
                x = np.arange(len(daily_df))
                y = daily_df["stock_level"].values
                trend_y, rmse = get_trend_poly(x, y, stock_model)
                
                if trend_y is not None:
                     label = f'Trend ({stock_model}, RMSE={rmse:.2f})'
                     plt.plot(daily_df.index, trend_y, "r--", linewidth=2, label=label)
                     context['stock_rmse'] = round(rmse, 2)

            plt.title('Stock Level History (Simulated)')
            plt.xlabel('Date')
            plt.ylabel('Units Remaining')
            plt.legend()
            plt.grid(True)
            plt.tight_layout()

            buf2 = io.BytesIO()
            plt.savefig(buf2, format='png')
            buf2.seek(0)
            string2 = base64.b64encode(buf2.read())
            context["stock_graph"] = urllib.parse.quote(string2)
            plt.close()

        return context
