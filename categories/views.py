from django.urls import reverse_lazy
from app.mixins import (
    BaseListView, BaseCreateView, BaseUpdateView, BaseDetailView,
    BaseDeleteView, BaseTrashListView, BaseRestoreView, BaseHardDeleteView,
)
from . import models, forms
from .filters import CategoryFilter


class CategoryListView(BaseListView):
    model = models.Category
    template_name = 'category_list.html'
    htmx_template_name = 'category_list_partial.html'
    context_object_name = 'categories'
    permission_required = 'categories.view_category'
    filterset_class = CategoryFilter


class CategoryCreateView(BaseCreateView):
    model = models.Category
    template_name = 'category_create.html'
    form_class = forms.CategoryForm
    success_url = reverse_lazy('categories:category_list')
    permission_required = 'categories.add_category'
    success_message = "Categoria criada com sucesso!"


class CategoryUpdateView(BaseUpdateView):
    model = models.Category
    template_name = 'category_update.html'
    form_class = forms.CategoryForm
    success_url = reverse_lazy('categories:category_list')
    permission_required = 'categories.change_category'
    success_message = "Categoria atualizada com sucesso!"


class CategoryDetailView(BaseDetailView):
    model = models.Category
    template_name = 'category_detail.html'
    context_object_name = 'category'
    permission_required = 'categories.view_category'


class CategoryDeleteView(BaseDeleteView):
    model = models.Category
    template_name = 'category_delete.html'
    success_url = reverse_lazy('categories:category_list')
    permission_required = 'categories.delete_category'
    success_message = "Categoria excluida com sucesso!"
    protected_error_message = (
        "Nao e possivel eliminar esta categoria porque esta a ser utilizada por produtos."
    )


class CategoryTrashListView(BaseTrashListView):
    model = models.Category
    template_name = 'category_trash.html'
    htmx_template_name = 'category_trash_partial.html'
    context_object_name = 'categories'
    permission_required = 'categories.delete_category'


class CategoryRestoreView(BaseRestoreView):
    model = models.Category
    redirect_url = 'category_trash'
    permission_required = 'categories.delete_category'
    success_message = "Categoria restaurada com sucesso!"


class CategoryHardDeleteView(BaseHardDeleteView):
    model = models.Category
    redirect_url = 'category_trash'
    permission_required = 'categories.delete_category'
    success_message = "Categoria eliminada permanentemente!"
    protected_error_message = (
        "Nao e possivel eliminar permanentemente esta categoria."
    )
