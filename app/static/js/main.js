// HTMX loading bar
document.body.addEventListener('htmx:beforeRequest', function () {
    var bar = document.getElementById('htmx-loading-bar');
    if (bar) bar.classList.add('active');
});
document.body.addEventListener('htmx:afterRequest', function () {
    var bar = document.getElementById('htmx-loading-bar');
    if (bar) bar.classList.remove('active');
});

document.addEventListener('DOMContentLoaded', function () {

    // Comma-to-dot converter (with delegation for HTMX-loaded inputs)
    document.addEventListener('input', function (e) {
        if (!e.target.matches) return;
        if (e.target.matches('input[type="number"], .decimal-input')) {
            if (e.target.value.includes(',')) {
                e.target.value = e.target.value.replace(',', '.');
            }
        }
    });

    // Mobile sidebar toggle
    var sidebarToggle = document.querySelector('#sidebarToggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function () {
            var sidebar = document.querySelector('.sge-sidebar');
            if (sidebar) sidebar.classList.toggle('show');
        });
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', function (e) {
        var tag = document.activeElement.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

        if (e.key === 'Escape') {
            var modal = document.querySelector('.modal.show');
            if (modal) {
                var bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            }
        }
    });

    // Delete confirmation modal
    var deleteModal = document.getElementById('deleteModal');
    if (deleteModal) {
        deleteModal.addEventListener('show.bs.modal', function (event) {
            var button = event.relatedTarget;
            var url = button.getAttribute('data-delete-url');
            var message = button.getAttribute('data-delete-message') || 'Tem certeza que deseja eliminar este registo?';
            document.getElementById('deleteModalForm').action = url;
            document.getElementById('deleteModalBody').textContent = message;
        });
    }

    // Bulk select/delete (delegated for HTMX-loaded partials)
    var bulkBar = document.getElementById('bulk-actions');
    if (bulkBar) {
        // Delegate checkbox changes on the wrapper that HTMX replaces
        var wrapper = document.getElementById('list-table-wrapper');
        var listenEl = wrapper || document;

        listenEl.addEventListener('change', function (e) {
            if (!e.target.matches) return;
            if (e.target.matches('.bulk-checkbox')) {
                updateBulkBar();
            }
            if (e.target.matches('#select-all')) {
                var checkboxes = document.querySelectorAll('.bulk-checkbox');
                checkboxes.forEach(function (cb) { cb.checked = e.target.checked; });
                updateBulkBar();
            }
        });

        var clearBtn = document.getElementById('clear-selection');
        if (clearBtn) {
            clearBtn.addEventListener('click', function () {
                var checkboxes = document.querySelectorAll('.bulk-checkbox');
                checkboxes.forEach(function (cb) { cb.checked = false; });
                var selectAll = document.getElementById('select-all');
                if (selectAll) selectAll.checked = false;
                updateBulkBar();
            });
        }

        var confirmBtn = document.getElementById('confirm-bulk-delete');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', function () {
                var bulkForm = document.getElementById('bulk-form');
                if (bulkForm) bulkForm.submit();
            });
        }
    }

    function updateBulkBar() {
        var checked = document.querySelectorAll('.bulk-checkbox:checked').length;
        var selectedCount = document.getElementById('selected-count');
        var bulkCountEl = document.getElementById('bulk-count');
        var selectAll = document.getElementById('select-all');
        var checkboxes = document.querySelectorAll('.bulk-checkbox');
        if (selectedCount) selectedCount.textContent = checked;
        if (bulkCountEl) bulkCountEl.textContent = checked;
        if (bulkBar) bulkBar.classList.toggle('d-none', checked === 0);
        if (selectAll) selectAll.checked = checked === checkboxes.length && checked > 0;
    }

    // Confirm dialog for forms with data-confirm attribute
    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (!form.matches) return;
        if (form.matches('[data-confirm]')) {
            if (!confirm(form.getAttribute('data-confirm'))) {
                e.preventDefault();
            }
        }
    });

    // Sidebar close button (data-close-sidebar)
    document.addEventListener('click', function (e) {
        if (!e.target.matches) return;
        var btn = e.target.closest('[data-close-sidebar]');
        if (btn) {
            var sidebar = document.querySelector('.sge-sidebar');
            if (sidebar) sidebar.classList.remove('show');
        }
    });

    // Print trigger button (.js-print-trigger)
    document.addEventListener('click', function (e) {
        if (!e.target.matches) return;
        if (e.target.closest('.js-print-trigger')) {
            window.print();
        }
    });

    // Collapse icon toggler for filter panels
    var filterCollapse = document.getElementById('filterCollapse');
    if (filterCollapse) {
        filterCollapse.addEventListener('show.bs.collapse', function () {
            var icon = document.getElementById('filterToggleIcon');
            if (icon) {
                icon.classList.remove('bi-chevron-down');
                icon.classList.add('bi-chevron-up');
            }
        });
        filterCollapse.addEventListener('hide.bs.collapse', function () {
            var icon = document.getElementById('filterToggleIcon');
            if (icon) {
                icon.classList.remove('bi-chevron-up');
                icon.classList.add('bi-chevron-down');
            }
        });
    }

});

