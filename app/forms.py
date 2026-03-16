from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Product, ProductImage

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class ProductForm(forms.ModelForm):
    available_weights_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500',
            'placeholder': 'e.g., 2kg, 5kg, 10kg, 20kg'
        }),
        label="Available Weights (comma separated)"
    )
    
    stock_per_weight_input = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500',
            'rows': 3,
            'placeholder': 'e.g., 2kg:10, 5kg:8, 10kg:5, 20kg:3'
        }),
        label="Stock per Weight (format: weight:quantity)"
    )
    
    class Meta:
        model = Product
        fields = [
            'product_id', 'name', 'brand', 'category', 'price',
            'description', 'image'
        ]
        widgets = {
            'product_id': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500'
            }),
            'brand': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500',
                'rows': 4
            }),
            'image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make ALL fields optional
        for field in self.fields:
            self.fields[field].required = False
        
        if self.instance.pk:
            # Populate the simple inputs from JSON fields
            if self.instance.available_weights:
                self.initial['available_weights_input'] = ', '.join(self.instance.available_weights)
            
            if self.instance.stock_per_weight:
                stock_pairs = [f"{k}:{v}" for k, v in self.instance.stock_per_weight.items()]
                self.initial['stock_per_weight_input'] = ', '.join(stock_pairs)
    
    def clean_available_weights_input(self):
        data = self.cleaned_data['available_weights_input']
        if not data:
            return []
        
        # Parse comma-separated weights
        weights = [w.strip() for w in data.split(',') if w.strip()]
        return weights
    
    def clean_stock_per_weight_input(self):
        data = self.cleaned_data['stock_per_weight_input']
        if not data:
            return {}
        
        stock_dict = {}
        # Parse format like "2kg:10, 5kg:8, 10kg:5"
        pairs = data.split(',')
        for pair in pairs:
            if ':' in pair:
                weight, qty = pair.split(':')
                weight = weight.strip()
                try:
                    qty = int(qty.strip())
                    stock_dict[weight] = qty
                except ValueError:
                    pass  # Ignore invalid entries
        
        return stock_dict

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make image field optional
        self.fields['image'].required = False

# Custom formset that doesn't require existing instances to have IDs
from django.forms.models import BaseInlineFormSet

class BaseProductImageFormSet(BaseInlineFormSet):
    def _construct_form(self, i, **kwargs):
        """Override to avoid ID validation for existing forms"""
        form = super()._construct_form(i, **kwargs)
        # Make the ID field not required
        if 'id' in form.fields:
            form.fields['id'].required = False
        return form
    
    def clean(self):
        """Skip validation for empty forms"""
        for form in self.forms:
            if form.instance.pk is None and not form.has_changed():
                form.cleaned_data = {}
                form._errors = {}

# Create formset with extra=3 and can_delete=True
ProductImageFormSet = forms.inlineformset_factory(
    Product, 
    ProductImage, 
    form=ProductImageForm,
    formset=BaseProductImageFormSet,
    extra=3, 
    max_num=3, 
    can_delete=True,
    min_num=0,
    validate_min=False
)