from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, DeleteView, UpdateView
from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django_filters.views import FilterView
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from products.models import Product
from app.mixins import ExportMixin, HtmxMixin
from . import models, forms
from .filters import OutflowFilter


class OutflowListView(LoginRequiredMixin, PermissionRequiredMixin, HtmxMixin, ExportMixin, FilterView):
    model = models.Outflow
    template_name = 'outflow_list.html'
    htmx_template_name = 'outflow_list_partial.html'
    context_object_name = 'outflows'
    permission_required = 'outflows.view_outflow'
    paginate_by = 10
    filterset_class = OutflowFilter
    export_columns = [
        ('Produto', 'product.title'),
        ('Cliente', 'customer.name'),
        ('Quantidade', 'quantity'),
        ('Preco', 'price'),
        ('Data', 'created_at'),
    ]

    def get_queryset(self):
        qs = super().get_queryset().select_related('product', 'customer')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        self.filterset = self.filterset_class(self.request.GET, queryset=qs)
        return self.filterset.qs


class OutflowCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = models.Outflow
    template_name = 'outflow_create.html'
    form_class = forms.OutflowForm
    success_url = reverse_lazy('outflows:outflow_list')
    permission_required = 'outflows.add_outflow'
    success_message = "Saída registada com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = getattr(self.request, 'tenant', None)
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                product_qs = Product.objects
                tenant = getattr(self.request, 'tenant', None)
                if tenant:
                    product_qs = product_qs.filter(tenant=tenant)
                product = product_qs.select_for_update().get(pk=form.cleaned_data['product'].pk)
                quantity = form.cleaned_data['quantity']
                if quantity > product.quantity:
                    form.add_error('quantity', f'A quantidade excede o estoque disponivel ({product.quantity}).')
                    return self.form_invalid(form)
                outflow = form.save(commit=False)
                if tenant:
                    outflow.tenant = tenant
                if not outflow.price:
                    outflow.price = product.selling_price
                outflow.save()
        except Product.DoesNotExist:
            form.add_error('product', 'O produto selecionado já não existe.')
            return self.form_invalid(form)
        return super().form_valid(form)


class OutflowUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = models.Outflow
    template_name = 'outflow_update.html'
    form_class = forms.OutflowForm
    success_url = reverse_lazy('outflows:outflow_list')
    permission_required = 'outflows.change_outflow'
    success_message = "Saída atualizada com sucesso!"

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

    def form_valid(self, form):
        try:
            with transaction.atomic():
                outflow_qs = models.Outflow.objects
                product_qs = Product.objects
                tenant = getattr(self.request, 'tenant', None)
                if tenant:
                    outflow_qs = outflow_qs.filter(tenant=tenant)
                    product_qs = product_qs.filter(tenant=tenant)
                outflow = outflow_qs.select_for_update().get(pk=self.object.pk)
                product = product_qs.select_for_update().get(pk=form.cleaned_data['product'].pk)
                new_qty = form.cleaned_data['quantity']
                delta = new_qty - outflow.quantity
                if delta > 0 and delta > product.quantity:
                    form.add_error(
                        'quantity',
                        f'Aumento de quantidade excede o estoque disponível ({product.quantity}).',
                    )
                    return self.form_invalid(form)
        except (Product.DoesNotExist, models.Outflow.DoesNotExist):
            form.add_error('product', 'O produto ou a saída selecionada já não existe.')
            return self.form_invalid(form)
        return super().form_valid(form)


class OutflowDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Outflow
    template_name = 'outflow_detail.html'
    context_object_name = 'outflow'
    permission_required = 'outflows.view_outflow'

    def get_queryset(self):
        qs = super().get_queryset().select_related('product', 'customer')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        deliveries = self.object.deliveries.all().select_related('driver')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            deliveries = deliveries.filter(tenant=tenant)
        context['deliveries'] = deliveries
        return context


class OutflowDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = models.Outflow
    template_name = 'outflow_delete.html'
    success_url = reverse_lazy('outflows:outflow_list')
    permission_required = 'outflows.delete_outflow'

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
            messages.success(request, "Saida excluida com sucesso!")
        except ProtectedError:
            messages.error(request, "Nao e possivel eliminar esta saida porque esta a ser utilizada por entregas.")
        return redirect(self.success_url)


class OutflowTrashListView(LoginRequiredMixin, PermissionRequiredMixin, HtmxMixin, ListView):
    model = models.Outflow
    template_name = 'outflow_trash.html'
    htmx_template_name = 'outflow_trash_partial.html'
    context_object_name = 'outflows'
    permission_required = 'outflows.delete_outflow'
    paginate_by = 10

    def get_queryset(self):
        qs = models.Outflow.all_objects.filter(is_deleted=True).select_related('product', 'customer')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs


class OutflowRestoreView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'outflows.delete_outflow'

    def post(self, request, pk):
        qs = models.Outflow.all_objects
        tenant = getattr(request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        outflow = qs.get(pk=pk)
        outflow.restore()
        messages.success(request, "Saida restaurada com sucesso!")
        return redirect('outflows:outflow_trash')


@method_decorator(ratelimit(key='user_or_ip', rate='10/m', method='POST', block=True), name='post')
class OutflowHardDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'outflows.delete_outflow'

    def post(self, request, pk):
        from django.db.models import ProtectedError
        try:
            qs = models.Outflow.all_objects
            tenant = getattr(request, 'tenant', None)
            if tenant:
                qs = qs.filter(tenant=tenant)
            outflow = qs.get(pk=pk)
            outflow.hard_delete()
            messages.success(request, "Saida eliminada permanentemente!")
        except ProtectedError:
            messages.error(request, "Nao e possivel eliminar permanentemente esta saida.")
        return redirect('outflows:outflow_trash')


class DeliveryCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = models.Delivery
    template_name = 'delivery_create.html'
    form_class = forms.DeliveryForm
    success_message = "Entrega registada com sucesso!"
    permission_required = 'outflows.add_delivery'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = getattr(self.request, 'tenant', None)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = models.Outflow.objects
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        context['outflow'] = get_object_or_404(qs, pk=self.kwargs['pk'])
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                outflow_qs = models.Outflow.objects
                tenant = getattr(self.request, 'tenant', None)
                if tenant:
                    outflow_qs = outflow_qs.filter(tenant=tenant)
                outflow = outflow_qs.select_for_update().select_related('product').get(
                    pk=self.kwargs['pk']
                )
                product_qs = Product.objects
                if tenant:
                    product_qs = product_qs.filter(tenant=tenant)
                product = product_qs.select_for_update().get(pk=outflow.product_id)
                quantity = form.cleaned_data['quantity']
                if quantity > outflow.quantity_pending:
                    form.add_error('quantity', f'A quantidade excede o pendente ({outflow.quantity_pending}).')
                    return self.form_invalid(form)
                if quantity > product.quantity:
                    form.add_error('quantity', f'A quantidade excede o estoque disponível ({product.quantity}).')
                    return self.form_invalid(form)
                form.instance.outflow = outflow
                if tenant:
                    form.instance.tenant = tenant
        except (Product.DoesNotExist, models.Outflow.DoesNotExist):
            form.add_error(None, 'O registo associado já não existe.')
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('outflows:outflow_detail', kwargs={'pk': self.kwargs['pk']})


class DeliveryConfirmWeightView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = models.Delivery
    template_name = 'delivery_confirm_weight.html'
    fields = ['actual_quantity']
    success_message = "Peso real confirmado com sucesso!"
    permission_required = 'outflows.change_delivery'

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs

    def form_valid(self, form):
        actual_quantity = form.cleaned_data['actual_quantity']

        with transaction.atomic():
            delivery_qs = models.Delivery.objects
            tenant = getattr(self.request, 'tenant', None)
            if tenant:
                delivery_qs = delivery_qs.filter(tenant=tenant)
            delivery = delivery_qs.select_for_update().get(pk=self.object.pk)
            if delivery.is_confirmed:
                form.add_error(None, "Esta entrega já foi confirmada.")
                return self.form_invalid(form)
            self.object = delivery
            form.instance = delivery
            self.object.actual_quantity = actual_quantity
            self.object.is_confirmed = True

        return super().form_valid(form)

    def get_success_url(self):
        delivery = self.get_object()
        return reverse_lazy('outflows:outflow_detail', kwargs={'pk': delivery.outflow.id})

class DeliveryShippingGuideView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Delivery
    template_name = 'delivery_shipping_guide.html'
    context_object_name = 'delivery'
    permission_required = 'outflows.view_delivery'

    def get_queryset(self):
        qs = super().get_queryset().select_related('outflow__product', 'outflow__customer', 'driver')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs


class DeliveryDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'outflows.delete_delivery'

    def post(self, request, pk):
        from django.db.models import ProtectedError
        qs = models.Delivery.objects
        tenant = getattr(request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        delivery = get_object_or_404(qs, pk=pk)
        outflow_pk = delivery.outflow_id
        try:
            delivery.delete()
            messages.success(request, 'Entrega movida para o lixo.')
        except ProtectedError:
            messages.error(request, 'Não é possível eliminar esta entrega porque está associada a outros registos.')
        return redirect('outflows:outflow_detail', pk=outflow_pk)


class DeliveryTrashListView(LoginRequiredMixin, PermissionRequiredMixin, HtmxMixin, ListView):
    model = models.Delivery
    template_name = 'delivery_trash.html'
    htmx_template_name = 'delivery_trash_partial.html'
    context_object_name = 'deliveries'
    permission_required = 'outflows.delete_delivery'
    paginate_by = 10

    def get_queryset(self):
        qs = models.Delivery.all_objects.filter(is_deleted=True).select_related(
            'outflow__product', 'outflow__customer', 'driver',
        )
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs


class DeliveryRestoreView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'outflows.delete_delivery'

    def post(self, request, pk):
        qs = models.Delivery.all_objects
        tenant = getattr(request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        delivery = qs.get(pk=pk)
        try:
            delivery.restore()
            messages.success(request, 'Entrega restaurada com sucesso!')
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('outflows:delivery_trash')


@method_decorator(ratelimit(key='user_or_ip', rate='10/m', method='POST', block=True), name='post')
class DeliveryHardDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'outflows.delete_delivery'

    def post(self, request, pk):
        from django.db.models import ProtectedError
        qs = models.Delivery.all_objects
        tenant = getattr(request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        delivery = qs.get(pk=pk)
        try:
            delivery.hard_delete()
            messages.success(request, 'Entrega eliminada permanentemente.')
        except ProtectedError:
            messages.error(request, 'Nao e possivel eliminar permanentemente esta entrega.')
        return redirect('outflows:delivery_trash')
