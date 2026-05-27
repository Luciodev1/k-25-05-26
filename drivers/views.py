from django.urls import reverse_lazy
from app.mixins import (
    BaseListView, BaseCreateView, BaseUpdateView, BaseDetailView,
    BaseDeleteView, BaseTrashListView, BaseRestoreView, BaseHardDeleteView,
)
from .models import Driver
from .forms import DriverForm
from .filters import DriverFilter


class DriverListView(BaseListView):
    model = Driver
    template_name = 'driver_list.html'
    htmx_template_name = 'driver_list_partial.html'
    context_object_name = 'drivers'
    permission_required = 'drivers.view_driver'
    filterset_class = DriverFilter


class DriverCreateView(BaseCreateView):
    model = Driver
    template_name = 'driver_create.html'
    form_class = DriverForm
    success_url = reverse_lazy('drivers:driver_list')
    permission_required = 'drivers.add_driver'
    success_message = "Motorista registado com sucesso!"


class DriverUpdateView(BaseUpdateView):
    model = Driver
    template_name = 'driver_update.html'
    form_class = DriverForm
    success_url = reverse_lazy('drivers:driver_list')
    permission_required = 'drivers.change_driver'
    success_message = "Dados do motorista atualizados com sucesso!"


class DriverDetailView(BaseDetailView):
    model = Driver
    template_name = 'driver_detail.html'
    context_object_name = 'driver'
    permission_required = 'drivers.view_driver'


class DriverDeleteView(BaseDeleteView):
    model = Driver
    template_name = 'driver_delete.html'
    success_url = reverse_lazy('drivers:driver_list')
    permission_required = 'drivers.delete_driver'
    success_message = "Motorista excluido com sucesso!"
    protected_error_message = (
        "Nao e possivel eliminar este motorista porque esta a ser utilizado por entregas."
    )


class DriverTrashListView(BaseTrashListView):
    model = Driver
    template_name = 'driver_trash.html'
    htmx_template_name = 'driver_trash_partial.html'
    context_object_name = 'drivers'
    permission_required = 'drivers.delete_driver'


class DriverRestoreView(BaseRestoreView):
    model = Driver
    redirect_url = 'drivers:driver_trash'
    permission_required = 'drivers.delete_driver'
    success_message = "Motorista restaurado com sucesso!"


class DriverHardDeleteView(BaseHardDeleteView):
    model = Driver
    redirect_url = 'drivers:driver_trash'
    permission_required = 'drivers.delete_driver'
    success_message = "Motorista eliminado permanentemente!"
    protected_error_message = "Não é possível eliminar permanentemente este motorista porque está associado a entregas."
