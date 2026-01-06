from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'sku', 'current_stock', 'minimum_stock_level', 'suppliers']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'sku': forms.TextInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'current_stock': forms.NumberInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'minimum_stock_level': forms.NumberInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'suppliers': forms.SelectMultiple(attrs={'class': 'shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
        }
