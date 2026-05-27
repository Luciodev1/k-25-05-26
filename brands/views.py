from django.urls import reverse_lazy
from app.mixins import (
    BaseListView, BaseCreateView, BaseUpdateView, BaseDetailView,
    BaseDeleteView, BaseTrashListView, BaseRestoreView, BaseHardDeleteView,
)
from . import models, forms
from .filters import BrandFilter


class BrandListView(BaseListView):
    model = models.Brand
    template_name = 'brand_list.html'
    htmx_template_name = 'brand_list_partial.html'
    context_object_name = 'brands'
    permission_required = 'brands.view_brand'
    filterset_class = BrandFilter


class BrandCreateView(BaseCreateView):
    model = models.Brand
    template_name = 'brand_create.html'
    form_class = forms.BrandForm
    success_url = reverse_lazy('brands:brand_list')
    permission_required = 'brands.add_brand'
    success_message = "Marca criada com sucesso!"


class BrandUpdateView(BaseUpdateView):
    model = models.Brand
    template_name = 'brand_update.html'
    form_class = forms.BrandForm
    success_url = reverse_lazy('brands:brand_list')
    permission_required = 'brands.change_brand'
    success_message = "Marca atualizada com sucesso!"


class BrandDetailView(BaseDetailView):
    model = models.Brand
    template_name = 'brand_detail.html'
    context_object_name = 'brand'
    permission_required = 'brands.view_brand'


class BrandDeleteView(BaseDeleteView):
    model = models.Brand
    template_name = 'brand_delete.html'
    success_url = reverse_lazy('brands:brand_list')
    permission_required = 'brands.delete_brand'
    success_message = "Marca excluida com sucesso!"
    protected_error_message = (
        "Nao e possivel eliminar esta marca porque esta a ser utilizada por produtos."
    )


class BrandTrashListView(BaseTrashListView):
    model = models.Brand
    template_name = 'brand_trash.html'
    htmx_template_name = 'brand_trash_partial.html'
    context_object_name = 'brands'
    permission_required = 'brands.delete_brand'


class BrandRestoreView(BaseRestoreView):
    model = models.Brand
    redirect_url = 'brand_trash'
    permission_required = 'brands.delete_brand'
    success_message = "Marca restaurada com sucesso!"


class BrandHardDeleteView(BaseHardDeleteView):
    model = models.Brand
    redirect_url = 'brand_trash'
    permission_required = 'brands.delete_brand'
    success_message = "Marca eliminada permanentemente!"
    protected_error_message = (
        "Nao e possivel eliminar permanentemente esta marca."
    )
