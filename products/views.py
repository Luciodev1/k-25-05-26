from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.views import View
from django.shortcuts import redirect
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django_filters.views import FilterView
from app.mixins import ExportMixin, HtmxMixin, GestorRequiredMixin
from . import models, forms
from .filters import ProductFilter


class ProductListView(LoginRequiredMixin, PermissionRequiredMixin, HtmxMixin, ExportMixin, FilterView):
    model = models.Product
    template_name = 'product_list.html'
    htmx_template_name = 'product_list_partial.html'
    context_object_name = 'products'
    permission_required = 'products.view_product'
    paginate_by = 10
    filterset_class = ProductFilter
    export_columns = [
        ('Titulo', 'title'),
        ('Categoria', 'category.name'),
        ('Marca', 'brand.name'),
        ('N/Serie', 'serial_number'),
        ('Preco Custo', 'cost_price'),
        ('Preco Venda', 'selling_price'),
        ('Quantidade', 'quantity'),
    ]

    def get_queryset(self):
        qs = super().get_queryset().select_related('category', 'brand')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        self.filterset = self.filterset_class(self.request.GET, queryset=qs)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from categories.models import Category
        from brands.models import Brand
        tenant = getattr(self.request, 'tenant', None)
        cats = Category.objects.only('id', 'name')
        brands = Brand.objects.only('id', 'name')
        if tenant:
            cats = cats.filter(tenant=tenant)
            brands = brands.filter(tenant=tenant)
        context['categories'] = cats
        context['brands'] = brands
        context['filters'] = {
            'title': self.request.GET.get('title', ''),
            'category': self.request.GET.get('category', ''),
            'brand': self.request.GET.get('brand', ''),
            'min_price': self.request.GET.get('min_price', ''),
            'max_price': self.request.GET.get('max_price', ''),
            'stock_status': self.request.GET.get('stock_status', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
        }
        return context


class ProductCreateView(GestorRequiredMixin, SuccessMessageMixin, CreateView):
    model = models.Product
    template_name = 'product_create.html'
    form_class = forms.ProductForm
    success_url = reverse_lazy('products:product_list')
    success_message = "Produto criado com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = getattr(self.request, 'tenant', None)
        return kwargs

    def form_valid(self, form):
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            form.instance.tenant = tenant
        return super().form_valid(form)


class ProductUpdateView(GestorRequiredMixin, SuccessMessageMixin, UpdateView):
    model = models.Product
    template_name = 'product_update.html'
    form_class = forms.ProductForm
    success_url = reverse_lazy('products:product_list')
    success_message = "Produto atualizado com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = getattr(self.request, 'tenant', None)
        return kwargs

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs


class ProductDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Product
    template_name = 'product_detail.html'
    context_object_name = 'product'
    permission_required = 'products.view_product'

    def get_queryset(self):
        qs = super().get_queryset().select_related('category', 'brand')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs


class ProductDeleteView(GestorRequiredMixin, DeleteView):
    model = models.Product
    template_name = 'product_delete.html'
    success_url = reverse_lazy('products:product_list')

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs

    def post(self, request, *args, **kwargs):
        from django.db.models import ProtectedError
        try:
            obj = self.get_object()
            obj.delete()
            messages.success(request, "Produto excluido com sucesso!")
            return redirect(self.success_url)
        except ProtectedError:
            messages.error(request, "Nao e possivel eliminar este produto porque esta a ser utilizado por outros registos.")
            return redirect(self.success_url)


class ProductBulkDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = ('products.delete_product',)

    def handle_no_permission(self):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Nao tem permissao para eliminar produtos.")

    def post(self, request, *args, **kwargs):
        from django.db.models import ProtectedError
        ids = request.POST.getlist('ids')
        if ids:
            with transaction.atomic():
                count = 0
                errors = []
                qs = models.Product.objects.filter(id__in=ids)
                tenant = getattr(request, 'tenant', None)
                if tenant:
                    qs = qs.filter(tenant=tenant)
                for product in qs:
                    try:
                        product.delete()
                        count += 1
                    except ProtectedError:
                        errors.append(str(product))
            if count:
                messages.success(request, f"{count} produto(s) eliminado(s) com sucesso!")
            if errors:
                messages.error(request, f"Não foi possível eliminar: {', '.join(errors)}")
        return redirect('products:product_list')


class ProductTrashListView(LoginRequiredMixin, PermissionRequiredMixin, HtmxMixin, ListView):
    model = models.Product
    template_name = 'product_trash.html'
    htmx_template_name = 'product_trash_partial.html'
    context_object_name = 'products'
    permission_required = 'products.delete_product'
    paginate_by = 10

    def get_queryset(self):
        qs = models.Product.all_objects.filter(is_deleted=True).select_related('category', 'brand')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs


class ProductRestoreView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'products.delete_product'

    def post(self, request, pk):
        qs = models.Product.all_objects
        tenant = getattr(request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        product = qs.get(pk=pk)
        product.restore()
        messages.success(request, "Produto restaurado com sucesso!")
        return redirect('products:product_trash')


class ProductHardDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'products.delete_product'

    def post(self, request, pk):
        from django.db.models import ProtectedError
        try:
            qs = models.Product.all_objects
            tenant = getattr(request, 'tenant', None)
            if tenant:
                qs = qs.filter(tenant=tenant)
            product = qs.get(pk=pk)
            product.hard_delete()
            messages.success(request, "Produto eliminado permanentemente!")
        except ProtectedError:
            messages.error(request, "Nao e possivel eliminar permanentemente este produto.")
        return redirect('products:product_trash')
