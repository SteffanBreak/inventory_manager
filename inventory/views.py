import io
import base64
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from django.db.models import Sum, F, ExpressionWrapper, FloatField, Q
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from .models import Product, ConsumptionLog
from .forms import ProductForm
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView


def clean_data(df, remove_outliers=False, smoothing=False):
    if df.empty:
        return df
    df = df.copy()
    df["units_used"] = pd.to_numeric(df["units_used"], errors="coerce").fillna(0)
    if remove_outliers and len(df) >= 4:
        q1 = df["units_used"].quantile(0.25)
        q3 = df["units_used"].quantile(0.75)
        iqr = q3 - q1
        low = q1 - 1.5 * iqr
        high = q3 + 1.5 * iqr
        df = df[(df["units_used"] >= low) & (df["units_used"] <= high)]
    if smoothing and len(df) >= 3:
        df["units_used"] = df["units_used"].rolling(window=3, min_periods=1).mean()
    return df


def get_trend_poly(x, y, degree):
    coeffs = np.polyfit(x, y, degree)
    p = np.poly1d(coeffs)
    yhat = p(x)
    rmse = np.sqrt(np.mean((y - yhat) ** 2))
    return p, rmse


class ProductListView(ListView):
    model = Product
    template_name = "inventory/product_list.html"
    context_object_name = "products"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().select_related("supplier")
        supplier = self.request.GET.get("supplier")
        status = self.request.GET.get("status")
        if supplier:
            qs = qs.filter(supplier__name__icontains=supplier)
        if status == "ok":
            qs = qs.filter(quantity_in_stock__gt=F("minimum_stock_level"))
        elif status == "low":
            qs = qs.filter(quantity_in_stock__gt=0, quantity_in_stock__lte=F("minimum_stock_level"))
        elif status == "critical":
            qs = qs.filter(quantity_in_stock__lte=0)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = context.get("products")
        ok = 0
        low = 0
        critical = 0
        if products is not None:
            for p in products:
                if p.quantity_in_stock <= 0:
                    critical += 1
                elif p.quantity_in_stock <= p.minimum_stock_level:
                    low += 1
                else:
                    ok += 1
        context["status_ok"] = ok
        context["status_low"] = low
        context["status_critical"] = critical
        context["filter_supplier"] = self.request.GET.get("supplier", "")
        context["filter_status"] = self.request.GET.get("status", "")
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = "inventory/product_detail.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        enable_outliers = self.request.GET.get("remove_outliers") == "1"
        enable_smoothing = self.request.GET.get("enable_smoothing") == "1"
        consumption_model = int(self.request.GET.get("consumption_model", 1))
        stock_model = int(self.request.GET.get("stock_model", 1))

        logs_qs = ConsumptionLog.objects.filter(product=product).order_by("-date")
        paginator = Paginator(logs_qs, 10)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context["page_obj"] = page_obj
        context["remove_outliers"] = "1" if enable_outliers else "0"
        context["enable_smoothing"] = "1" if enable_smoothing else "0"
        context["consumption_model"] = consumption_model
        context["stock_model"] = stock_model

        df = pd.DataFrame(list(logs_qs.values("date", "units_used")))
        if not df.empty:
            df = df.sort_values("date")
            df = clean_data(df, remove_outliers=enable_outliers, smoothing=enable_smoothing)
        context["has_data"] = not df.empty

        if not df.empty:
            df["x"] = (df["date"] - df["date"].min()).dt.days.astype(float)
            x = df["x"].values
            y = df["units_used"].values.astype(float)

            try:
                p, rmse = get_trend_poly(x, y, consumption_model)
            except Exception:
                p, rmse = get_trend_poly(x, y, 1)

            context["rmse_consumption"] = float(rmse)

            days_to_predict = 30
            x_future = np.arange(0, max(x.max(), 1) + days_to_predict + 1, 1)
            y_pred = p(x_future)

            y_pred = np.clip(y_pred, 0, None)

            plt.figure(figsize=(10, 4))
            plt.plot(df["date"], y, marker="o", label="Consumption")
            future_dates = [df["date"].min() + timedelta(days=int(d)) for d in x_future]
            plt.plot(future_dates, y_pred, label="Trend")
            plt.title("Consumption Trend")
            plt.xlabel("Date")
            plt.ylabel("Units Used")
            plt.legend()
            plt.grid(True)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            string = base64.b64encode(buf.read())
            context["graph"] = string.decode()
            plt.close()

            avg_daily = float(np.mean(y)) if len(y) else 0.0
            if avg_daily > 0:
                days_left = int(product.quantity_in_stock / avg_daily) if product.quantity_in_stock > 0 else 0
            else:
                days_left = None

            context["avg_daily_consumption"] = round(avg_daily, 2)
            context["days_left"] = days_left

            if days_left is not None:
                prediction_date = timezone.now().date() + timedelta(days=days_left)
            else:
                prediction_date = None
            context["prediction_date"] = prediction_date

            df2 = df.copy()
            df2 = df2.sort_values("date")
            df2["x"] = (df2["date"] - df2["date"].min()).dt.days.astype(float)
            x2 = df2["x"].values
            stock = []
            remaining = product.quantity_in_stock
            for u in df2["units_used"].values:
                remaining = remaining - float(u)
                stock.append(remaining)
            stock = np.array(stock, dtype=float)

            try:
                p2, rmse2 = get_trend_poly(x2, stock, stock_model)
            except Exception:
                p2, rmse2 = get_trend_poly(x2, stock, 1)

            context["rmse_stock"] = float(rmse2)

            x_future2 = np.arange(0, max(x2.max(), 1) + days_to_predict + 1, 1)
            stock_pred = p2(x_future2)

            plt.figure(figsize=(10, 4))
            plt.plot(df2["date"], stock, marker="o", label="Stock (calculated)")
            future_dates2 = [df2["date"].min() + timedelta(days=int(d)) for d in x_future2]
            plt.plot(future_dates2, stock_pred, label="Trend")
            plt.axhline(float(product.minimum_stock_level), linestyle="--", label="Minimum stock level")
            plt.title("Stock Level Trend")
            plt.xlabel("Date")
            plt.ylabel("Units Remaining")
            plt.legend()
            plt.grid(True)
            plt.tight_layout()

            buf2 = io.BytesIO()
            plt.savefig(buf2, format="png")
            buf2.seek(0)
            string2 = base64.b64encode(buf2.read())
            context["stock_graph"] = string2.decode()
            plt.close()

        return context


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


class ProductDeleteView(DeleteView):
    model = Product
    template_name = "inventory/product_confirm_delete.html"
    success_url = reverse_lazy("product_list")
