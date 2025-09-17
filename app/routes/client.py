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
from app.models.reseñas import Reseña
from app.models.guardados import Guardado
from flask_login import login_required, current_user, logout_user
import logging
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from sqlalchemy.orm import joinedload
from werkzeug.security import check_password_hash, generate_password_hash
from decimal import Decimal
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.graphics.shapes import Circle
from reportlab.graphics import renderPDF
from reportlab.lib.colors import white
from reportlab.platypus import SimpleDocTemplate
from PIL import Image, ImageDraw
import io

bp = Blueprint('client', __name__, url_prefix='/client')

# Configurar logging básico
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# IVA (16% como estándar, ajustable)
IVA_RATE = Decimal("0.16")

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
    try:
        productos = Producto.query.all()
        return render_template('productos.html', productos=productos)
    except Exception as e:
        logger.error(f"Error al cargar productos: {str(e)}")
        flash(f"Ocurrió un error al cargar los productos: {str(e)}. Por favor, intenta de nuevo.", "danger")
        return redirect(url_for('auth.login'))

@bp.route('/citas')
@login_required
def citas():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    servicio_id = request.args.get('servicio_id')
    servicios = Servicio.query.all()
    return render_template('citas.html', servicios=servicios, servicio_id=servicio_id)

@bp.route('/agregar_carrito/<int:item_id>', methods=['GET'])
@login_required
def agregar_carrito(item_id):
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    try:
        logger.debug(f"Intentando agregar item {item_id} para usuario {current_user.id_usuario}")
        carrito = Carrito.query.filter_by(id_usuario=current_user.id_usuario, estado='activo').first()
        if not carrito:
            logger.debug(f"No se encontró carrito activo, creando nuevo para id_usuario={current_user.id_usuario}")
            carrito = Carrito(id_usuario=current_user.id_usuario, estado='activo')
            db.session.add(carrito)
            db.session.flush()
            logger.debug(f"Carrito creado con id_carrito={carrito.id_carrito}")
        else:
            logger.debug(f"Carrito existente encontrado con id_carrito={carrito.id_carrito}")

        # Determinar si es producto o servicio
        producto = Producto.query.get(item_id)
        servicio = Servicio.query.get(item_id)
        if producto:
            if not hasattr(producto, 'precio') or producto.precio is None:
                raise ValueError("El producto no tiene precio definido.")
            if not hasattr(producto, 'stock') or producto.stock is None or producto.stock <= 0:
                flash("No hay stock disponible.", "danger")
                return redirect(url_for('client.productos'))
            detalle = DetalleCarrito(
                id_carrito=carrito.id_carrito,
                id_producto=item_id,
                cantidad=1,
                precio_unitario=producto.precio,
                id_servicio=None
            )
        elif servicio:
            if not hasattr(servicio, 'precio') or servicio.precio is None:
                raise ValueError("El servicio no tiene precio definido.")
            detalle = DetalleCarrito(
                id_carrito=carrito.id_carrito,
                id_servicio=item_id,
                cantidad=1,
                precio_unitario=servicio.precio,
                id_producto=None
            )
        else:
            raise ValueError("Item no encontrado o no es un producto ni un servicio.")

        db.session.add(detalle)
        db.session.flush()
        logger.debug(f"Detalle creado con id_detalle_carrito={detalle.id_detalle_carrito}")
        db.session.commit()
        logger.debug(f"Detalle agregado al carrito {carrito.id_carrito} para item {item_id}")
        flash("Item agregado al carrito.", "success")
        return redirect(url_for('client.productos' if producto else 'client.servicios'))
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Error de integridad al agregar al carrito: {str(e)} - Usuario: {current_user.id_usuario}, Item: {item_id}, Carrito: {carrito.id_carrito if carrito else 'None'}")
        flash("Error de integridad al agregar el item. Verifica los datos e intenta de nuevo.", "danger")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al agregar al carrito: {str(e)} - Usuario: {current_user.id_usuario}, Item: {item_id}, Carrito: {carrito.id_carrito if 'carrito' in locals() else 'None'}")
        flash(f"Ocurrió un error al agregar el item al carrito: {str(e)}. Por favor, intenta de nuevo.", "danger")
    return redirect(url_for('client.productos' if producto else 'client.servicios'))

@bp.route('/carrito')
@login_required
def carrito():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    logger.debug(f"Cargando carrito para usuario: {current_user.id_usuario}")
    carrito = Carrito.query.options(
        joinedload(Carrito.detalles).joinedload(DetalleCarrito.producto),
        joinedload(Carrito.detalles).joinedload(DetalleCarrito.servicio)
    ).filter_by(id_usuario=current_user.id_usuario, estado='activo').first()
    logger.debug(f"Carrito cargado: {carrito}")
    if carrito:
        logger.debug(f"Detalles cargados: {[d.id_detalle_carrito for d in carrito.detalles]}")
        for detalle in carrito.detalles:
            logger.debug(f"Detalle {detalle.id_detalle_carrito}: producto = {detalle.producto}, servicio = {detalle.servicio}")
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

@bp.route('/actualizar_cantidad/<int:detalle_id>', methods=['POST'])
@login_required
def actualizar_cantidad(detalle_id):
    if current_user.rol != 'cliente':
        return jsonify({'success': False, 'message': 'Acceso denegado. Solo para clientes.'}), 403
    detalle = DetalleCarrito.query.get_or_404(detalle_id)
    if detalle.carrito and detalle.carrito.id_usuario != current_user.id_usuario:
        return jsonify({'success': False, 'message': 'No tienes permiso para modificar este item.'}), 403

    data = request.get_json()
    increment = data.get('increment', False)
    producto = Producto.query.get(detalle.id_producto) if detalle.id_producto else None

    if detalle.id_producto and (not producto or not hasattr(producto, 'stock') or producto.stock is None):
        return jsonify({'success': False, 'message': 'Producto no disponible o sin stock.'}), 400

    nueva_cantidad = detalle.cantidad
    if increment:
        if detalle.id_producto and producto.stock > detalle.cantidad:
            nueva_cantidad += 1
        elif not detalle.id_producto or (detalle.id_servicio and nueva_cantidad < 10):  # Límite arbitrario para servicios
            nueva_cantidad += 1
        else:
            return jsonify({'success': False, 'message': 'No hay suficiente stock disponible o límite alcanzado.'}), 400
    else:
        if detalle.cantidad > 1:
            nueva_cantidad -= 1
        else:
            return jsonify({'success': False, 'message': 'La cantidad no puede ser menor a 1.'}), 400

    detalle.cantidad = nueva_cantidad
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'cantidad': nueva_cantidad,
            'precio_unitario': detalle.precio_unitario
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al actualizar cantidad: {str(e)}")
        return jsonify({'success': False, 'message': f'Ocurrió un error: {str(e)}'}), 500

@bp.route('/procesar_compra', methods=['GET', 'POST'])
@login_required
def procesar_compra():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    carrito = Carrito.query.options(
        joinedload(Carrito.detalles).joinedload(DetalleCarrito.producto),
        joinedload(Carrito.detalles).joinedload(DetalleCarrito.servicio)
    ).filter_by(id_usuario=current_user.id_usuario, estado='activo').first()
    if not carrito or not carrito.detalles:
        flash("No tienes items en el carrito para procesar.", "danger")
        return redirect(url_for('client.carrito'))
    if request.method == 'POST':
        try:
            # Verificar y actualizar stock para productos
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
            subtotal = sum(Decimal(str(detalle.cantidad)) * Decimal(str(detalle.precio_unitario)) for detalle in carrito.detalles if detalle.id_producto or detalle.id_servicio)
            iva = subtotal * IVA_RATE
            total = subtotal + iva
            venta = Venta(id_usuario=current_user.id_usuario, fecha_venta=datetime.utcnow(), total=total)
            db.session.add(venta)
            db.session.commit()

            # Crear detalles de venta basados en el carrito
            detalles_venta = []
            for detalle in carrito.detalles:
                if detalle.id_producto or detalle.id_servicio:
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

            # Generar factura con ReportLab
            nombre_archivo = f'factura_{current_user.id_usuario}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            ruta_archivo = os.path.join(os.path.dirname(__file__), '..', 'static', nombre_archivo)
            c = canvas.Canvas(ruta_archivo, pagesize=letter)
            c.setFont("Helvetica-Bold", 16)

            # Logo circular con tamaño ajustado
            logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'casa-bella-logo.jpeg')
            if os.path.exists(logo_path):
                # Create circular clipped image
                def create_circular_image(image_path, size=80):
                    img = Image.open(image_path)
                    img = img.convert("RGBA")
                    img.thumbnail((size, size), Image.Resampling.LANCZOS)
                    mask = Image.new('L', (size, size), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.ellipse((0, 0, size, size), fill=255)
                    output = Image.new('RGBA', (size, size), (255, 255, 255, 0))
                    output.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
                    output.putalpha(mask)
                    img_buffer = io.BytesIO()
                    output.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    return img_buffer
                
                circular_logo = create_circular_image(logo_path, 80)
                logo_x = 50
                logo_y = 720
                logo_size = 80
                c.drawImage(ImageReader(circular_logo), logo_x, logo_y, logo_size, logo_size)

            c.setFont("Helvetica-Bold", 18)
            c.drawString(150, 760, "Casa Bella")
            c.setFont("Helvetica", 14)
            c.drawString(150, 740, "Salón de Belleza y Distribuidora")
            
            c.setStrokeColorRGB(0.2, 0.4, 0.8)
            c.setLineWidth(2)
            c.line(50, 710, 550, 710)

            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, 680, "FACTURA")
            c.setFont("Helvetica", 10)
            c.drawString(400, 680, f"Fecha: {venta.fecha_venta.strftime('%Y-%m-%d %H:%M')}")
            
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, 660, "DATOS DEL CLIENTE:")
            c.setFont("Helvetica", 10)
            c.drawString(50, 645, f"Nombre: {current_user.nombre}")
            c.drawString(50, 630, f"Email: {current_user.email or 'No proporcionado'}")
            c.drawString(50, 615, f"Teléfono: {current_user.telefono or 'No proporcionado'}")

            y = 580
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, "PRODUCTOS/SERVICIOS:")
            c.setStrokeColorRGB(0.8, 0.8, 0.8)
            c.line(50, y-5, 550, y-5)
            
            y -= 25
            c.setFont("Helvetica", 9)

            for detalle in detalles_venta:
                if detalle.id_producto:
                    producto = Producto.query.get(detalle.id_producto)
                    if producto:
                        subtotal_item = Decimal(str(detalle.cantidad)) * Decimal(str(detalle.precio_unitario))
                        c.drawString(60, y, f"{producto.nombre} x {detalle.cantidad} - ${subtotal_item.quantize(Decimal('0.01'))}")
                        y -= 20
                elif detalle.id_servicio:
                    servicio = Servicio.query.get(detalle.id_servicio)
                    if servicio:
                        subtotal_item = Decimal(str(detalle.cantidad)) * Decimal(str(detalle.precio_unitario))
                        c.drawString(60, y, f"{servicio.nombre} x {detalle.cantidad} - ${subtotal_item.quantize(Decimal('0.01'))}")
                        y -= 20

            c.drawString(50, y-10, "─" * 70)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(400, y-30, f"Subtotal: ${subtotal.quantize(Decimal('0.01'))}")
            c.drawString(400, y-45, f"IVA (16%): ${iva.quantize(Decimal('0.01'))}")
            c.setFont("Helvetica-Bold", 12)
            c.drawString(400, y-65, f"TOTAL: ${total.quantize(Decimal('0.01'))}")
            
            c.setFont("Helvetica-Oblique", 10)
            c.drawString(50, y-100, "¡Gracias por confiar en Casa Bella!")
            c.drawString(50, y-115, "Tu belleza es nuestra pasión")
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
        total = venta.total if venta.total else Decimal('0.00')
        detalles_venta = DetalleVenta.query.filter_by(id_venta=venta_id).options(joinedload(DetalleVenta.producto)).all()
        subtotal = sum(Decimal(str(detalle.cantidad)) * Decimal(str(detalle.precio_unitario)) for detalle in detalles_venta)
        iva = subtotal * IVA_RATE

        nombre_archivo = f'factura_{current_user.id_usuario}_{venta_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        ruta_archivo = os.path.join(os.path.dirname(__file__), '..', 'static', nombre_archivo)
        c = canvas.Canvas(ruta_archivo, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)

        # Logo circular con tamaño ajustado
        logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'casa-bella-logo.jpeg')
        if os.path.exists(logo_path):
            # Create circular clipped image (same function as above)
            def create_circular_image(image_path, size=80):
                img = Image.open(image_path)
                img = img.convert("RGBA")
                img.thumbnail((size, size), Image.Resampling.LANCZOS)
                
                mask = Image.new('L', (size, size), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, size, size), fill=255)
                
                output = Image.new('RGBA', (size, size), (255, 255, 255, 0))
                output.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
                output.putalpha(mask)
                
                img_buffer = io.BytesIO()
                output.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                return img_buffer
            
            circular_logo = create_circular_image(logo_path, 80)
            logo_x = 50
            logo_y = 720
            logo_size = 80
            c.drawImage(ImageReader(circular_logo), logo_x, logo_y, logo_size, logo_size)

        c.setFont("Helvetica-Bold", 18)
        c.drawString(150, 760, "Casa Bella")
        c.setFont("Helvetica", 14)
        c.drawString(150, 740, "Salón de Belleza y Distribuidora")
        
        c.setStrokeColorRGB(0.2, 0.4, 0.8)
        c.setLineWidth(2)
        c.line(50, 710, 550, 710)

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 680, "FACTURA")
        c.setFont("Helvetica", 10)
        c.drawString(400, 680, f"Fecha: {venta.fecha_venta.strftime('%Y-%m-%d %H:%M') if venta.fecha_venta else 'Sin fecha'}")
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, 660, "DATOS DEL CLIENTE:")
        c.setFont("Helvetica", 10)
        c.drawString(50, 645, f"Nombre: {current_user.nombre}")
        c.drawString(50, 630, f"Email: {current_user.email or 'No proporcionado'}")
        c.drawString(50, 615, f"Teléfono: {current_user.telefono or 'No proporcionado'}")

        y = 580
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "PRODUCTOS/SERVICIOS:")
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.line(50, y-5, 550, y-5)
        
        y -= 25
        c.setFont("Helvetica", 9)

        for detalle in detalles_venta:
            if detalle.id_producto:
                producto = detalle.producto
                if producto:
                    subtotal_item = Decimal(str(detalle.cantidad)) * Decimal(str(detalle.precio_unitario))
                    c.drawString(60, y, f"{producto.nombre} x {detalle.cantidad} - ${subtotal_item.quantize(Decimal('0.01'))}")
                    y -= 20
            elif detalle.id_servicio:
                servicio = Servicio.query.get(detalle.id_servicio)
                if servicio:
                    subtotal_item = Decimal(str(detalle.cantidad)) * Decimal(str(detalle.precio_unitario))
                    c.drawString(60, y, f"{servicio.nombre} x {detalle.cantidad} - ${subtotal_item.quantize(Decimal('0.01'))}")
                    y -= 20

        c.drawString(50, y-10, "─" * 70)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(400, y-30, f"Subtotal: ${subtotal.quantize(Decimal('0.01'))}")
        c.drawString(400, y-45, f"IVA (16%): ${iva.quantize(Decimal('0.01'))}")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(400, y-65, f"TOTAL: ${total.quantize(Decimal('0.01'))}")
        
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(50, y-100, "¡Gracias por confiar en Casa Bella!")
        c.drawString(50, y-115, "Tu belleza es nuestra pasión")
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
    total = sum(Decimal(str(d.cantidad)) * Decimal(str(d.precio_unitario)) for d in detalles if d.id_producto or d.id_servicio)
    table_rows = []
    for detalle in detalles:
        if detalle.id_producto:
            producto = Producto.query.get(detalle.id_product)
            if producto:
                row = f"{producto.nombre} & {detalle.cantidad or 0} & ${Decimal(str(detalle.precio_unitario or 0)).quantize(Decimal('0.01'))} & ${(Decimal(str(detalle.cantidad or 0)) * Decimal(str(detalle.precio_unitario or 0))).quantize(Decimal('0.01'))} \\\\"
                table_rows.append(row)
        elif detalle.id_servicio:
            servicio = Servicio.query.get(detalle.id_servicio)
            if servicio:
                row = f"{servicio.nombre} & {detalle.cantidad or 0} & ${Decimal(str(detalle.precio_unitario or 0)).quantize(Decimal('0.01'))} & ${(Decimal(str(detalle.cantidad or 0)) * Decimal(str(detalle.precio_unitario or 0))).quantize(Decimal('0.01'))} \\\\"
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
\\multicolumn{{3}}{{r}}{{Total}} & ${total.quantize(Decimal('0.01'))} \\\\
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
    fecha_hora_str = request.form.get('fecha_hora')
    if not current_user.is_authenticated or not current_user.id_usuario:
        flash("Error: Usuario no autenticado correctamente.", "danger")
        return redirect(url_for('auth.login'))

    try:
        # Convertir fecha_hora a objeto datetime
        fecha_hora = datetime.strptime(fecha_hora_str, '%Y-%m-%dT%H:%M')

        # Definir horarios del salón
        horarios = {
            0: {'inicio': datetime.strptime('09:00', '%H:%M').time(), 'fin': datetime.strptime('19:00', '%H:%M').time()},  # Lunes
            1: {'inicio': datetime.strptime('08:00', '%H:%M').time(), 'fin': datetime.strptime('19:00', '%H:%M').time()},  # Martes
            2: {'inicio': datetime.strptime('09:00', '%H:%M').time(), 'fin': datetime.strptime('19:00', '%H:%M').time()},  # Miércoles
            3: None,  # Jueves (CERRADO)
            4: {'inicio': datetime.strptime('09:00', '%H:%M').time(), 'fin': datetime.strptime('19:00', '%H:%M').time()},  # Viernes
            5: {'inicio': datetime.strptime('09:00', '%H:%M').time(), 'fin': datetime.strptime('19:00', '%H:%M').time()},  # Sábado
            6: {'inicio': datetime.strptime('09:00', '%H:%M').time(), 'fin': datetime.strptime('18:00', '%H:%M').time()}   # Domingo
        }

        # Obtener el día de la semana (0 = Lunes, 6 = Domingo)
        dia_semana = fecha_hora.weekday()

        # Verificar si el día está cerrado
        if horarios[dia_semana] is None:
            flash("Hora o día no disponible en el horario. El salón está cerrado este día (Jueves).", "danger")
            return redirect(url_for('client.citas'))

        # Obtener el horario del día
        horario_dia = horarios[dia_semana]
        hora_solicitada = fecha_hora.time()

        # Verificar si la hora está dentro del rango permitido
        if hora_solicitada < horario_dia['inicio'] or hora_solicitada > horario_dia['fin']:
            flash("Hora o día no disponible en el horario. Por favor, selecciona una hora dentro del rango permitido.", "danger")
            return redirect(url_for('client.citas'))

        # Verificar incrementos de 30 minutos (opcional, ajustable)
        minutos = hora_solicitada.minute
        if minutos % 30 != 0:
            flash("Hora no disponible. Las citas solo están disponibles en incrementos de 30 minutos (e.g., 9:00, 9:30).", "danger")
            return redirect(url_for('client.citas'))

        # Verificar si la cita es en el pasado
        if fecha_hora < datetime.now():
            flash("No puedes reservar citas en el pasado.", "danger")
            return redirect(url_for('client.citas'))

        # Crear la cita
        cita = Cita(
            id_usuario=current_user.id_usuario,
            id_servicio=servicio_id,
            fecha_hora=fecha_hora,
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

@bp.route('/agregar_favorito/<string:item_type>/<int:item_id>', methods=['POST'])
@login_required
def agregar_favorito(item_type, item_id):
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    
    try:
        # Validate item_type
        if item_type not in ['producto', 'servicio']:
            raise ValueError("Tipo de item inválido.")
        
        # Check if the item is already in favorites
        favorito = Guardado.query.filter_by(
            id_usuario=current_user.id_usuario,
            id_producto=item_id if item_type == 'producto' else None,
            id_servicio=item_id if item_type == 'servicio' else None
        ).first()
        
        # Get item details for flash messages
        if item_type == 'producto':
            item = Producto.query.get_or_404(item_id)
            item_name = item.nombre
        else:
            item = Servicio.query.get_or_404(item_id)
            item_name = item.nombre
        
        if favorito:
            # If already in favorites, remove it
            db.session.delete(favorito)
            db.session.commit()
            flash(f"{item_name} eliminado de favoritos.", "info")
            return jsonify({'success': True, 'added': False, 'message': f"{item_name} eliminado de favoritos."})
        else:
            # Add to favorites
            nuevo_favorito = Guardado(
                id_usuario=current_user.id_usuario,
                id_producto=item_id if item_type == 'producto' else None,
                id_servicio=item_id if item_type == 'servicio' else None
            )
            db.session.add(nuevo_favorito)
            db.session.commit()
            flash(f"{item_name} agregado a favoritos.", "success")
            return jsonify({'success': True, 'added': True, 'message': f"{item_name} agregado a favoritos."})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al gestionar favorito: {str(e)}")
        flash(f"Ocurrió un error: {str(e)}.", "danger")
        return jsonify({'success': False, 'message': f"Ocurrió un error: {str(e)}"}), 500

@bp.route('/favoritos')
@login_required
def favoritos():
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    
    try:
        favoritos = Guardado.query.options(
            joinedload(Guardado.producto),
            joinedload(Guardado.servicio)
        ).filter_by(id_usuario=current_user.id_usuario).all()
        return render_template('favoritos.html', favoritos=favoritos)
    except Exception as e:
        logger.error(f"Error al cargar favoritos: {str(e)}")
        flash(f"Ocurrió un error al cargar los favoritos: {str(e)}.", "danger")
        return redirect(url_for('client.productos'))

@bp.route('/check_favorito/<string:item_type>/<int:item_id>', methods=['GET'])
@login_required
def check_favorito(item_type, item_id):
    if current_user.rol != 'cliente':
        return jsonify({'success': False, 'message': 'Acceso denegado. Solo para clientes.'}), 403
    
    try:
        if item_type not in ['producto', 'servicio']:
            return jsonify({'success': False, 'message': 'Tipo de item inválido.'}), 400
        
        favorito = Guardado.query.filter_by(
            id_usuario=current_user.id_usuario,
            id_producto=item_id if item_type == 'producto' else None,
            id_servicio=item_id if item_type == 'servicio' else None
        ).first()
        return jsonify({'success': True, 'is_favorite': favorito is not None})
    except Exception as e:
        logger.error(f"Error al verificar favorito: {str(e)}")
        return jsonify({'success': False, 'message': f"Ocurrió un error: {str(e)}"}), 500
    

@bp.route('/reseñas/<string:item_type>/<int:item_id>', methods=['GET', 'POST'])
@login_required
def resenas(item_type, item_id):
    if current_user.rol != 'cliente':
        flash("Acceso denegado. Solo para clientes.", "danger")
        return redirect(url_for('auth.login'))
    
    try:
        # Validate item_type
        if item_type not in ['producto', 'servicio']:
            raise ValueError("Tipo de item inválido.")
        
        # Get item details
        if item_type == 'producto':
            item = Producto.query.get_or_404(item_id)
            item_name = item.nombre
        else:
            item = Servicio.query.get_or_404(item_id)
            item_name = item.nombre
        
        if request.method == 'POST':
            calificacion = request.form.get('calificacion', type=int)
            comentario = request.form.get('comentario', '').strip()
            
            # Validate input
            if not calificacion or calificacion < 1 or calificacion > 5:
                flash("La calificación debe estar entre 1 y 5.", "danger")
                return redirect(url_for('client.resenas', item_type=item_type, item_id=item_id))
            
            # Check if user already reviewed this item
            existing_review = Reseña.query.filter_by(
                id_usuario=current_user.id_usuario,
                id_producto=item_id if item_type == 'producto' else None,
                id_servicio=item_id if item_type == 'servicio' else None
            ).first()
            
            if existing_review:
                flash("Ya has dejado una reseña para este item.", "warning")
                return redirect(url_for('client.resenas', item_type=item_type, item_id=item_id))
            
            # Create new review
            new_review = Reseña(
                id_usuario=current_user.id_usuario,
                id_producto=item_id if item_type == 'producto' else None,
                id_servicio=item_id if item_type == 'servicio' else None,
                calificacion=calificacion,
                comentario=comentario
            )
            db.session.add(new_review)
            db.session.commit()
            flash(f"Reseña para {item_name} enviada correctamente.", "success")
            return redirect(url_for('client.resenas', item_type=item_type, item_id=item_id))
        
        # GET request: Load reviews
        reviews = Reseña.query.options(
            joinedload(Reseña.usuario)
        ).filter(
            (Reseña.id_producto == item_id) if item_type == 'producto' else (Reseña.id_servicio == item_id)
        ).all()
        
        return render_template('reseñas.html', item_type=item_type, item_id=item_id, item_name=item_name, reviews=reviews)
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al gestionar reseñas: {str(e)}")
        flash(f"Ocurrió un error: {str(e)}.", "danger")
        return redirect(url_for('client.productos' if item_type == 'producto' else 'client.servicios'))