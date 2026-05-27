"""Context processors for global template variables."""

# Map URL prefixes to breadcrumb labels
BREADCRUMB_MAP = {
    '/products/': 'Produtos',
    '/categories/': 'Categorias',
    '/brands/': 'Marcas',
    '/suppliers/': 'Fornecedores',
    '/customers/': 'Clientes',
    '/inflows/': 'Entradas',
    '/outflows/': 'Saidas',
    '/deliveries/': 'Entregas',
    '/drivers/': 'Motoristas',
    '/pagamentos/': 'Pagamentos',
    '/accounts/': 'Contas',
    '/reports/': 'Relatorios',
    '/auditoria/': 'Auditoria',
    '/users/': 'Utilizadores',
    '/grupos/': 'Grupos',
}


def breadcrumbs(request):
    """Generate breadcrumbs based on the current URL path."""
    path = request.path
    crumbs = []

    for prefix, label in BREADCRUMB_MAP.items():
        if path.startswith(prefix):
            crumbs.append({'label': label, 'url': prefix})
            # Add sub-page if applicable
            suffix = path[len(prefix):].strip('/')
            if suffix:
                if 'create' in suffix or 'novo' in suffix:
                    crumbs.append({'label': 'Novo', 'url': None})
                elif 'update' in suffix or 'editar' in suffix:
                    crumbs.append({'label': 'Editar', 'url': None})
                elif 'detail' in suffix or 'detalhe' in suffix:
                    crumbs.append({'label': 'Detalhe', 'url': None})
                elif 'delete' in suffix or 'eliminar' in suffix:
                    crumbs.append({'label': 'Eliminar', 'url': None})
                elif 'trash' in suffix or 'lixeira' in suffix:
                    crumbs.append({'label': 'Lixeira', 'url': None})
                elif 'restore' in suffix or 'restaurar' in suffix:
                    crumbs.append({'label': 'Restaurar', 'url': None})
                elif 'hard-delete' in suffix or 'eliminar-permanente' in suffix:
                    crumbs.append({'label': 'Eliminar Permanentemente', 'url': None})
            break

    return {'breadcrumbs': crumbs}
