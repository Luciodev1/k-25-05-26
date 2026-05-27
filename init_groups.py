import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

def setup_groups():
    groups = {
        'Administrador': [], # Full access (Superuser usually, but can be a group)
        'Gerente': [
            'view', 'add', 'change', 'delete'
        ],
        'Operador': [
            'view', 'add', 'change'
        ],
        'Financeiro': [
            'view_payment', 'add_payment', 'view_customeraccountentry', 'add_customeraccountentry',
            'view_supplieraccountentry', 'add_supplieraccountentry'
        ]
    }

    # Simplified approach: for Gerente and Operador, give them permissions for all stock models
    stock_apps = ['brands', 'categories', 'products', 'suppliers', 'customers', 'inflows', 'outflows', 'drivers', 'payments', 'accounts']
    
    for group_name, perms in groups.items():
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            print(f"Created group: {group_name}")
        
        if group_name == 'Administrador':
            # Give all permissions
            all_perms = Permission.objects.all()
            group.permissions.set(all_perms)
            continue

        group_perms = []
        for app in stock_apps:
            content_types = ContentType.objects.filter(app_label=app)
            for ct in content_types:
                for action in perms:
                    if '_' in action: # specific permission
                        p = Permission.objects.filter(codename=action).first()
                        if p: group_perms.append(p)
                    else: # generic action like 'view', 'add'
                        codename = f"{action}_{ct.model}"
                        p = Permission.objects.filter(codename=codename).first()
                        if p: group_perms.append(p)
        
        group.permissions.set(group_perms)
        print(f"Updated permissions for group: {group_name}")

if __name__ == '__main__':
    setup_groups()
