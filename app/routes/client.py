from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file
from app import db
from app.models.servicios import Servicio
from app.models.productos import Producto
from app.models.citas import Cita
from app.models.carrito import Carrito
from app.models.detalle_carrito import DetalleCarrito
from app.models.ventas import Venta
from app.models.detalle_ventas import DetalleVenta
from app.models.pagos import Pago
from app.models.inventario_movimientos import InventarioMovimiento
from app.models.users import Usuario
from flask_login import login_required, current_user, logout_user
import logging
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from sqlalchemy.orm import joinedload
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from werkzeug.security import check_password_hash, generate_password_hash

bp = Blueprint('client', __name__, url_prefix='/client')

# Configurar logging básico
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Contexto para todas las rutas del cliente
@bp.context_processor
def inject_carrito():
    if current_user.is_authenticated:
        carrito = Carrito.query.filter_by(id_usuario=current_user.id_usuario, estado='activo').first()
        return dict(carrito=carrito)
    return dict(carrito=None)

@bp.route('/servicios')
@login_required
def servicios():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    servicios = Servicio.query.all()
    return render_template('servicios.html', servicios=servicios)

@bp.route('/productos')
@login_required
def productos():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    productos = Producto.query.all()
    return render_template('productos.html', productos=productos)

@bp.route('/citas')
@login_required
def citas():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    servicio_id = request.args.get('servicio_id')
    servicios = Servicio.query.all()
    return render_template('citas.html', servicios=servicios, servicio_id=servicio_id)

@bp.route('/agregar_carrito/<int:producto_id>', methods=['GET'])
@login_required
def agregar_carrito(producto_id):
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    try:
        logger.debug(f"Intentando agregar producto {producto_id} para usuario {current_user.id_usuario}")
        carrito = Carrito.query.filter_by(id_usuario=current_user.id_usuario, estado='activo').first()
        if not carrito:
            logger.debug(f"No se encontró carrito activo, creando nuevo para id_usuario={current_user.id_usuario}")
            carrito = Carrito(id_usuario=current_user.id_usuario, estado='activo')
            db.session.add(carrito)
            db.session.flush()
            logger.debug(f"Carrito creado con id_carrito={carrito.id_carrito}")
        else:
            logger.debug(f"Carrito existente encontrado con id_carrito={carrito.id_carrito}")

        producto = Producto.query.get_or_404(producto_id)
        if not hasattr(producto, 'precio') or producto.precio is None:
            raise ValueError("El producto no tiene precio definido.")
        if not hasattr(producto, 'stock') or producto.stock is None or producto.stock <= 0:
            flash("No hay stock disponible.", "danger")
            return redirect(url_for('client.productos'))

        detalle = DetalleCarrito()
        detalle.id_carrito = carrito.id_carrito
        detalle.id_producto = producto_id
        detalle.cantidad = 1
        detalle.precio_unitario = producto.precio
        detalle.id_servicio = None
        db.session.add(detalle)
        db.session.flush()
        logger.debug(f"Detalle creado con id_detalle_carrito={detalle.id_detalle_carrito}")
        db.session.commit()
        logger.debug(f"Detalle agregado al carrito {carrito.id_carrito} para producto {producto_id}")
        flash("Producto agregado al carrito.", "success")
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Error de integridad al agregar al carrito: {str(e)} - Usuario: {current_user.id_usuario}, Producto: {producto_id}, Carrito: {carrito.id_carrito if carrito else 'None'}")
        flash("Error de integridad al agregar el producto. Verifica los datos e intenta de nuevo.", "danger")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al agregar al carrito: {str(e)} - Usuario: {current_user.id_usuario}, Producto: {producto_id}, Carrito: {carrito.id_carrito if 'carrito' in locals() else 'None'}")
        flash(f"Ocurrió un error al agregar el producto al carrito: {str(e)}. Por favor, intenta de nuevo.", "danger")
    return redirect(url_for('client.productos'))

@bp.route('/carrito')
@login_required
def carrito():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    carrito = Carrito.query.options(joinedload(Carrito.detalles).joinedload(DetalleCarrito.producto)).filter_by(id_usuario=current_user.id_usuario, estado='activo').first()
    logger.debug(f"Carrito cargado: {carrito}")
    if carrito:
        logger.debug(f"Detalles: {[d.id_detalle_carrito for d in carrito.detalles]}")
    else:
        logger.debug("No se encontró carrito activo")
    if not carrito:
        flash("No tienes un carrito activo.", "info")
    return render_template('carrito.html', carrito=carrito)

@bp.route('/eliminar_del_carrito/<int:detalle_id>', methods=['POST'])
@login_required
def eliminar_del_carrito(detalle_id):
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    detalle = DetalleCarrito.query.get_or_404(detalle_id)
    if detalle.carrito and detalle.carrito.id_usuario != current_user.id_usuario:
        flash("No tienes permiso para eliminar este item.", "danger")
        return redirect(url_for('auth.login'))
    try:
        db.session.delete(detalle)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Item eliminado del carrito.'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al eliminar del carrito: {str(e)}")
        return jsonify({'success': False, 'message': f'Ocurrió un error: {str(e)}'}), 500

@bp.route('/procesar_compra', methods=['GET', 'POST'])
@login_required
def procesar_compra():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    carrito = Carrito.query.options(joinedload(Carrito.detalles).joinedload(DetalleCarrito.producto)).filter_by(id_usuario=current_user.id_usuario, estado='activo').first()
    if not carrito or not carrito.detalles:
        flash("No tienes items en el carrito para procesar.", "danger")
        return redirect(url_for('client.carrito'))
    if request.method == 'POST':
        try:
            # Verificar y actualizar stock
            for detalle in carrito.detalles:
                if detalle.id_producto:
                    producto = Producto.query.get(detalle.id_producto)
                    if producto and (not hasattr(producto, 'stock') or producto.stock is None or producto.stock < detalle.cantidad):
                        db.session.rollback()
                        flash("Stock insuficiente para procesar la compra.", "danger")
                        return redirect(url_for('client.carrito'))
                    if producto:
                        producto.stock -= detalle.cantidad

            # Crear la venta
            total = sum(d.cantidad * d.precio_unitario for d in carrito.detalles if d.id_producto or d.id_servicio)
            venta = Venta(id_usuario=current_user.id_usuario, fecha_venta=datetime.utcnow(), total=total)
            db.session.add(venta)
            db.session.commit()

            # Crear detalles de venta basados en el carrito
            detalles_venta = []
            for detalle in carrito.detalles:
                if detalle.id_producto or detalle.id_servicio:  # Solo procesar si hay producto o servicio
                    detalle_venta = DetalleVenta(
                        id_venta=venta.id_venta,
                        id_producto=detalle.id_producto,
                        id_servicio=detalle.id_servicio,
                        cantidad=detalle.cantidad,
                        precio_unitario=detalle.precio_unitario
                    )
                    db.session.add(detalle_venta)
                    detalles_venta.append(detalle_venta)

            # Crear registro de pago
            metodo_pago = request.form.get('metodo_pago')
            if not metodo_pago:
                raise ValueError("Debe seleccionar un método de pago.")
            pago = Pago(id_venta=venta.id_venta, metodo_pago=metodo_pago, monto=total)
            db.session.add(pago)

            # Crear movimientos de inventario solo para productos
            for detalle in carrito.detalles:
                if detalle.id_producto:
                    movimiento = InventarioMovimiento(
                        id_producto=detalle.id_producto,
                        tipo_movimiento='salida',
                        cantidad=detalle.cantidad,
                        motivo=f'Venta ID: {venta.id_venta}'
                    )
                    db.session.add(movimiento)

            # Actualizar estado del carrito y eliminar detalles
            carrito.estado = 'completado'
            for detalle in carrito.detalles:
                db.session.delete(detalle)
            db.session.commit()

            # Generar factura con reportlab
            nombre_archivo = f'factura_{current_user.id_usuario}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            ruta_archivo = os.path.join(os.path.dirname(__file__), nombre_archivo)
            c = canvas.Canvas(ruta_archivo, pagesize=letter)
            c.setFont("Helvetica", 12)

            c.drawString(50, 750, "🛒 Casa Bella")
            c.drawString(50, 730, f"Cliente: {current_user.nombre}")
            c.drawString(50, 710, f"Fecha: {venta.fecha_venta.strftime('%Y-%m-%d %H:%M')}")
            y = 690

            c.drawString(50, y, "Productos/Servicios:")
            y -= 20
            for detalle in detalles_venta:
                if detalle.id_producto:
                    producto = Producto.query.get(detalle.id_producto)
                    if producto:
                        subtotal = detalle.cantidad * detalle.precio_unitario if detalle.cantidad and detalle.precio_unitario else 0.00
                        c.drawString(60, y, f"{producto.nombre} - {detalle.cantidad or 0} u. - ${subtotal:.2f}")
                        y -= 20
                elif detalle.id_servicio:
                    servicio = Servicio.query.get(detalle.id_servicio)
                    if servicio:
                        subtotal = detalle.cantidad * detalle.precio_unitario if detalle.cantidad and detalle.precio_unitario else 0.00
                        c.drawString(60, y, f"{servicio.nombre} - {detalle.cantidad or 0} u. - ${subtotal:.2f}")
                        y -= 20

            c.drawString(50, y-10, "-------------------------")
            c.drawString(50, y-30, f"TOTAL: ${total:.2f}")
            c.drawString(50, y-50, "¡Gracias por su compra!")
            c.save()

            if not os.path.exists(ruta_archivo):
                raise FileNotFoundError(f"El archivo {ruta_archivo} no se creó correctamente.")

            flash("Compra procesada con éxito. Descargando factura...", "success")
            response = send_file(ruta_archivo, as_attachment=True, download_name=nombre_archivo)
            if os.path.exists(ruta_archivo):
                os.remove(ruta_archivo)
            return response
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al procesar la compra: {str(e)}")
            flash(f"Ocurrió un error al procesar la compra: {str(e)}. Por favor, intenta de nuevo.", "danger")
            return redirect(url_for('client.carrito'))
    return render_template('procesar_compra.html', carrito=carrito)

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    # Obtener historial de compras con joinedload anidado, manejando casos donde id_usuario puede ser NULL
    ventas = Venta.query.filter((Venta.id_usuario == current_user.id_usuario) | (Venta.id_usuario == None)).options(
        joinedload(Venta.detalle_ventas).joinedload(DetalleVenta.producto)
    ).all()
    # Obtener historial de citas
    citas = Cita.query.filter_by(id_usuario=current_user.id_usuario).all()
    return render_template('dashboard_cliente.html', ventas=ventas, citas=citas)

@bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        try:
            nuevo_nombre = request.form.get('nombre')
            nuevo_email = request.form.get('email')
            nuevo_telefono = request.form.get('telefono')
            nueva_contraseña = request.form.get('contraseña')

            if nuevo_nombre and nuevo_nombre != current_user.nombre:
                current_user.nombre = nuevo_nombre
            if nuevo_email and nuevo_email != current_user.email:
                current_user.email = nuevo_email
            if nuevo_telefono and nuevo_telefono != current_user.telefono:
                current_user.telefono = nuevo_telefono
            if nueva_contraseña:
                current_user.contraseña = generate_password_hash(nueva_contraseña)

            current_user.rol = current_user.rol
            current_user.especialidad = current_user.especialidad
            current_user.fecha_registro = current_user.fecha_registro

            db.session.commit()
            flash("Perfil actualizado con éxito.", "success")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al actualizar perfil: {str(e)}")
            flash(f"Ocurrió un error al actualizar el perfil: {str(e)}. Por favor, intenta de nuevo.", "danger")
    # Consultar ventas y citas correctamente
    ventas = Venta.query.filter((Venta.id_usuario == current_user.id_usuario) | (Venta.id_usuario == None)).options(
        joinedload(Venta.detalle_ventas).joinedload(DetalleVenta.producto)
    ).all()
    citas = Cita.query.filter_by(id_usuario=current_user.id_usuario).all()
    return render_template('dashboard_cliente.html', ventas=ventas, citas=citas)

@bp.route('/borrar_perfil', methods=['POST'])
@login_required
def borrar_perfil():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    logger.info(f"Intentando borrar perfil del usuario {current_user.id_usuario}")
    try:
        usuario = current_user._get_current_object()
        if usuario.id_usuario != current_user.id_usuario:
            logger.warning("Intento de borrar un perfil diferente al autenticado")
            flash("No puedes borrar un perfil que no es el tuyo.", "danger")
            return redirect(url_for('client.dashboard'))
        logger.debug(f"Eliminando usuario con id_usuario={usuario.id_usuario}")
        db.session.delete(usuario)
        db.session.commit()
        logger.info(f"Usuario {usuario.id_usuario} eliminado con éxito")
        logout_user()
        flash("Perfil borrado. Has sido desconectado.", "success")
        return redirect(url_for('auth.login'))
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Error de integridad al borrar perfil: {str(e)} - Usuario: {current_user.id_usuario}")
        flash("No se puede borrar el perfil porque tiene datos asociados (como ventas o citas). Contacta al administrador.", "danger")
        return redirect(url_for('client.dashboard'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error inesperado al borrar perfil: {str(e)} - Usuario: {current_user.id_usuario}")
        flash(f"Ocurrió un error al borrar el perfil: {str(e)}. Por favor, intenta de nuevo.", "danger")
        return redirect(url_for('client.dashboard'))
@bp.route('/descargar_factura/<int:venta_id>', methods=['GET'])
@login_required
def descargar_factura(venta_id):
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    venta = Venta.query.get_or_404(venta_id)
    if venta.id_usuario != current_user.id_usuario:
        flash("No tienes permiso para descargar esta factura.", "danger")
        return redirect(url_for('client.dashboard'))
    try:
        total = venta.total if venta.total else 0.00  # Manejar caso donde total pueda ser NULL
        detalles_venta = DetalleVenta.query.filter_by(id_venta=venta_id).options(joinedload(DetalleVenta.producto)).all()

        nombre_archivo = f'factura_{current_user.id_usuario}_{venta_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        ruta_archivo = os.path.join(os.path.dirname(__file__), nombre_archivo)
        c = canvas.Canvas(ruta_archivo, pagesize=letter)
        c.setFont("Helvetica", 12)

        c.drawString(50, 750, "🛒 Casa Bella")
        c.drawString(50, 730, f"Cliente: {current_user.nombre}")
        c.drawString(50, 710, f"Fecha: {venta.fecha_venta.strftime('%Y-%m-%d %H:%M') if venta.fecha_venta else 'Sin fecha'}")
        y = 690

        c.drawString(50, y, "Productos/Servicios:")
        y -= 20
        for detalle in detalles_venta:
            if detalle.id_producto:
                producto = detalle.producto
                if producto:
                    subtotal = detalle.cantidad * detalle.precio_unitario if detalle.cantidad and detalle.precio_unitario else 0.00
                    c.drawString(60, y, f"{producto.nombre} - {detalle.cantidad or 0} u. - ${subtotal:.2f}")
                    y -= 20
            elif detalle.id_servicio:
                servicio = Servicio.query.get(detalle.id_servicio)
                if servicio:
                    subtotal = detalle.cantidad * detalle.precio_unitario if detalle.cantidad and detalle.precio_unitario else 0.00
                    c.drawString(60, y, f"{servicio.nombre} - {detalle.cantidad or 0} u. - ${subtotal:.2f}")
                    y -= 20

        c.drawString(50, y-10, "-------------------------")
        c.drawString(50, y-30, f"TOTAL: ${total:.2f}")
        c.drawString(50, y-50, "¡Gracias por su compra!")
        c.save()

        if not os.path.exists(ruta_archivo):
            raise FileNotFoundError(f"El archivo {ruta_archivo} no se creó correctamente.")

        flash("Descargando factura...", "success")
        response = send_file(ruta_archivo, as_attachment=True, download_name=nombre_archivo)
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)
        return response
    except Exception as e:
        logger.error(f"Error al descargar factura: {str(e)}")
        flash(f"Ocurrió un error al descargar la factura: {str(e)}. Por favor, intenta de nuevo.", "danger")
        return redirect(url_for('client.dashboard'))

@bp.route('/borrar_compra/<int:venta_id>', methods=['POST'])
@login_required
def borrar_compra(venta_id):
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    venta = Venta.query.get_or_404(venta_id)
    if venta.id_usuario != current_user.id_usuario:
        flash("No tienes permiso para borrar esta compra.", "danger")
        return redirect(url_for('client.dashboard'))
    try:
        DetalleVenta.query.filter_by(id_venta=venta_id).delete()
        db.session.delete(venta)
        db.session.commit()
        flash("Compra eliminada con éxito.", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al borrar compra: {str(e)}")
        flash(f"Ocurrió un error al borrar la compra: {str(e)}. Por favor, intenta de nuevo.", "danger")
    return redirect(url_for('client.dashboard'))

@bp.route('/borrar_cita/<int:cita_id>', methods=['POST'])
@login_required
def borrar_cita(cita_id):
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    cita = Cita.query.get_or_404(cita_id)
    if cita.id_usuario != current_user.id_usuario:
        flash("No tienes permiso para borrar esta cita.", "danger")
        return redirect(url_for('client.dashboard'))
    try:
        db.session.delete(cita)
        db.session.commit()
        flash("Cita eliminada con éxito.", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al borrar cita: {str(e)}")
        flash(f"Ocurrió un error al borrar la cita: {str(e)}. Por favor, intenta de nuevo.", "danger")
    return redirect(url_for('client.dashboard'))

# Función auxiliar para generar el contenido LaTeX de la factura (mantendremos por ahora, pero no se usará)
def generate_factura_latex(carrito, venta):
    detalles = carrito.detalles
    total = sum(d.cantidad * d.precio_unitario for d in detalles if d.id_producto or d.id_servicio)
    table_rows = []
    for detalle in detalles:
        if detalle.id_product:
            producto = Producto.query.get(detalle.id_producto)
            if producto:
                row = f"{producto.nombre} & {detalle.cantidad or 0} & ${detalle.precio_unitario or 0:.2f} & ${(detalle.cantidad or 0) * (detalle.precio_unitario or 0):.2f} \\\\"
                table_rows.append(row)
        elif detalle.id_servicio:
            servicio = Servicio.query.get(detalle.id_servicio)
            if servicio:
                row = f"{servicio.nombre} & {detalle.cantidad or 0} & ${detalle.precio_unitario or 0:.2f} & ${(detalle.cantidad or 0) * (detalle.precio_unitario or 0):.2f} \\\\"
                table_rows.append(row)
    table_content = '\n'.join(table_rows)

    return f"""\\documentclass[a4paper,12pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage{{geometry}}
\\geometry{{a4paper, margin=1in}}
\\usepackage{{booktabs}}
\\usepackage{{longtable}}
\\usepackage{{fancyhdr}}
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\fancyhead[L]{{Factura - Casa Bella}}
\\fancyfoot[C]{{Página \\thepage}}
\\usepackage{{amiri}} % Fuente para soporte de caracteres no latinos

\\begin{{document}}

\\begin{{center}}
\\textbf{{Factura}} \\\\
\\textbf{{Casa Bella}} \\\\
Fecha: {venta.fecha_venta.strftime('%Y-%m-%d %H:%M') if venta.fecha_venta else 'Sin fecha'} \\\\
Cliente: {current_user.nombre} (ID: {current_user.id_usuario}) \\\\
\\end{{center}}

\\begin{{longtable}}{{lccr}}
\\toprule
Producto/Servicio & Cantidad & Precio Unitario & Subtotal \\\\
\\midrule
\\endhead
\\midrule
\\multicolumn{{4}}{{r}}{{Continúa en la siguiente página}} \\\\
\\endfoot
\\bottomrule
\\endlastfoot
{table_content}
\\midrule
\\multicolumn{{3}}{{r}}{{Total}} & ${total:.2f} \\\\
\\bottomrule
\\end{{longtable}}

\\end{{document}}
""".replace('\n', '')

@bp.route('/reservar_cita', methods=['POST'])
@login_required
def reservar_cita():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    servicio_id = request.form.get('servicio_id')
    fecha_hora = request.form.get('fecha_hora')
    if not current_user.is_authenticated or not current_user.id_usuario:
        flash("Error: Usuario no autenticado correctamente.", "danger")
        return redirect(url_for('auth.login'))
    try:
        cita = Cita(
            id_usuario=current_user.id_usuario,
            id_servicio=servicio_id,
            fecha_hora=datetime.strptime(fecha_hora, '%Y-%m-%dT%H:%M'),
            estado='pendiente'
        )
        db.session.add(cita)
        db.session.commit()
        flash("Cita reservada con éxito.", "success")
    except ValueError as e:
        db.session.rollback()
        logger.error(f"Error en el formato de fecha: {str(e)}")
        flash("Error en el formato de la fecha. Usa YYYY-MM-DDTHH:MM.", "danger")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al reservar cita: {str(e)}")
        flash(f"Ocurrió un error al reservar la cita: {str(e)}. Por favor, intenta de nuevo.", "danger")
    return redirect(url_for('client.citas'))