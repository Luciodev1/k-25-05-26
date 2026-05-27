from django.urls import reverse_lazy
from app.mixins import (
    BaseListView, BaseCreateView, BaseUpdateView, BaseDetailView,
    BaseDeleteView, BaseTrashListView, BaseRestoreView, BaseHardDeleteView,
)
from . import models, forms
from .filters import SupplierFilter


class SupplierListView(BaseListView):
    model = models.Supplier
    template_name = 'supplier_list.html'
    htmx_template_name = 'supplier_list_partial.html'
    context_object_name = 'suppliers'
    permission_required = 'suppliers.view_supplier'
    filterset_class = SupplierFilter
    export_columns = [
        ('Nome', 'name'),
        ('Descricao', 'description'),
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        self.filterset = self.filterset_class(self.request.GET, queryset=qs)
        return self.filterset.qs


class SupplierCreateView(BaseCreateView):
    model = models.Supplier
    template_name = 'supplier_create.html'
    form_class = forms.SupplierForm
    success_url = reverse_lazy('suppliers:supplier_list')
    permission_required = 'suppliers.add_supplier'
    success_message = "Fornecedor criado com sucesso!"


class SupplierUpdateView(BaseUpdateView):
    model = models.Supplier
    template_name = 'supplier_update.html'
    form_class = forms.SupplierForm
    success_url = reverse_lazy('suppliers:supplier_list')
    permission_required = 'suppliers.change_supplier'
    success_message = "Fornecedor atualizado com sucesso!"


class SupplierDetailView(BaseDetailView):
    model = models.Supplier
    template_name = 'supplier_detail.html'
    context_object_name = 'supplier'
    permission_required = 'suppliers.view_supplier'


class SupplierDeleteView(BaseDeleteView):
    model = models.Supplier
    template_name = 'supplier_delete.html'
    success_url = reverse_lazy('suppliers:supplier_list')
    permission_required = 'suppliers.delete_supplier'
    success_message = "Fornecedor excluido com sucesso!"


class SupplierTrashListView(BaseTrashListView):
    model = models.Supplier
    template_name = 'supplier_trash.html'
    htmx_template_name = 'supplier_trash_partial.html'
    context_object_name = 'suppliers'
    permission_required = 'suppliers.delete_supplier'


class SupplierRestoreView(BaseRestoreView):
    model = models.Supplier
    redirect_url = 'suppliers:supplier_trash'
    permission_required = 'suppliers.delete_supplier'
    success_message = "Fornecedor restaurado com sucesso!"


class SupplierHardDeleteView(BaseHardDeleteView):
    model = models.Supplier
    redirect_url = 'suppliers:supplier_trash'
    permission_required = 'suppliers.delete_supplier'
    success_message = "Fornecedor eliminado permanentemente!"
