from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View


@method_decorator(login_required, name='dispatch')
class BaseReportView(View):
    """View base para relatórios com filtros e exportação."""
    template_name = None
    permission_required = 'reports.view_report'

    def get_filters(self, request):
        return {
            'date_from': request.GET.get('date_from', ''),
            'date_to': request.GET.get('date_to', ''),
        }
