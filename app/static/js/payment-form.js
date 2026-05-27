document.addEventListener('DOMContentLoaded', function () {
    var typeSelect = document.getElementById('id_type');
    var customerField = document.getElementById('customer_field');
    var supplierField = document.getElementById('supplier_field');

    if (!typeSelect || !customerField || !supplierField) return;

    function toggleFields() {
        if (typeSelect.value === 'RECEIPT') {
            customerField.style.display = 'block';
            supplierField.style.display = 'none';
        } else if (typeSelect.value === 'PAYMENT') {
            customerField.style.display = 'none';
            supplierField.style.display = 'block';
        } else {
            customerField.style.display = 'block';
            supplierField.style.display = 'block';
        }
    }

    typeSelect.addEventListener('change', toggleFields);
    toggleFields();
});
