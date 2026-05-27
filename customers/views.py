from django.urls import reverse_lazy
from app.mixins import (
    BaseListView, BaseCreateView, BaseUpdateView, BaseDetailView,
    BaseDeleteView, BaseTrashListView, BaseRestoreView, BaseHardDeleteView,
)
from . import models, forms
from .filters import CustomerFilter


class CustomerListView(BaseListView):
    model = models.Customer
    template_name = 'customer_list.html'
    htmx_template_name = 'customer_list_partial.html'
    context_object_name = 'customers'
    permission_required = 'customers.view_customer'
    filterset_class = CustomerFilter
    export_columns = [
        ('Nome', 'name'),
        ('Telefone', 'phone'),
        ('NIF', 'nif'),
        ('Endereco', 'address'),
        ('Email', 'email'),
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        self.filterset = self.filterset_class(self.request.GET, queryset=qs)
        return self.filterset.qs


class CustomerCreateView(BaseCreateView):
    model = models.Customer
    template_name = 'customer_create.html'
    form_class = forms.CustomerForm
    success_url = reverse_lazy('customers:customer_list')
    permission_required = 'customers.add_customer'
    success_message = "Cliente criado com sucesso!"


class CustomerUpdateView(BaseUpdateView):
    model = models.Customer
    template_name = 'customer_update.html'
    form_class = forms.CustomerForm
    success_url = reverse_lazy('customers:customer_list')
    permission_required = 'customers.change_customer'
    success_message = "Cliente atualizado com sucesso!"


class CustomerDetailView(BaseDetailView):
    model = models.Customer
    template_name = 'customer_detail.html'
    context_object_name = 'customer'
    permission_required = 'customers.view_customer'


class CustomerDeleteView(BaseDeleteView):
    model = models.Customer
    template_name = 'customer_delete.html'
    success_url = reverse_lazy('customers:customer_list')
    permission_required = 'customers.delete_customer'
    success_message = "Cliente excluido com sucesso!"


class CustomerTrashListView(BaseTrashListView):
    model = models.Customer
    template_name = 'customer_trash.html'
    htmx_template_name = 'customer_trash_partial.html'
    context_object_name = 'customers'
    permission_required = 'customers.delete_customer'


class CustomerRestoreView(BaseRestoreView):
    model = models.Customer
    redirect_url = 'customer_trash'
    permission_required = 'customers.delete_customer'
    success_message = "Cliente restaurado com sucesso!"


class CustomerHardDeleteView(BaseHardDeleteView):
    model = models.Customer
    redirect_url = 'customer_trash'
    permission_required = 'customers.delete_customer'
    success_message = "Cliente eliminado permanentemente!"
