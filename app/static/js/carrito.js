// static/js/carrito.js (opcional, si prefieres separar el JS)
function actualizarTotal() {
    let total = 0;
    document.querySelectorAll('.subtotal').forEach(subtotal => {
        total += parseFloat(subtotal.textContent.replace('$', ''));
    });
    document.querySelector('.total').textContent = `$${total.toFixed(2)}`;
}

function eliminarItem(detalleId) {
    if (confirm('¿Estás seguro de eliminar este item del carrito?')) {
        fetch(`/client/eliminar_del_carrito/${detalleId}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.querySelector(`tr[data-detalle-id="${detalleId}"]`).remove();
                actualizarTotal();
                if (document.querySelectorAll('tbody tr').length === 0) {
                    window.location.reload();
                }
            } else {
                alert(data.message);
            }
        })
        .catch(error => alert('Error al eliminar el item.'));
    }
}