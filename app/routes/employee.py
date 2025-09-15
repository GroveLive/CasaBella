from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file
from app import db
from app.models.citas import Cita
from app.models.servicios import Servicio
from app.models.productos import Producto
from app.models.ventas import Venta
from app.models.detalle_ventas import DetalleVenta
from app.models.pagos import Pago
from app.models.users import Usuario
from app.models.inventario_movimientos import InventarioMovimiento
from flask_login import login_required, current_user
import logging
from datetime import datetime
from decimal import Decimal
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import white
from PIL import Image, ImageDraw
import io

bp = Blueprint('employee', __name__, url_prefix='/employee')

# Configurar logging básico
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# IVA (16% como estándar, ajustable)
IVA_RATE = Decimal("0.16")

@bp.route('/dashboard')
@login_required
def empleado_dashboard():
    if current_user.rol != 'empleado':
        flash("Acceso denegado. Solo para empleados.", "danger")
        return redirect(url_for('auth.login'))
    citas_asignadas_count = Cita.query.filter_by(id_empleado=current_user.id_usuario, estado='pendiente').count()
    citas_pendientes_count = Cita.query.filter_by(estado='pendiente').count()
    return render_template('dashboard_empleado.html', citas_asignadas_count=citas_asignadas_count, citas_pendientes_count=citas_pendientes_count)

@bp.route('/trabajar_citas')
@login_required
def trabajar_citas():
    if current_user.rol != 'empleado':
        flash("Acceso denegado. Solo para empleados.", "danger")
        return redirect(url_for('auth.login'))
    citas = Cita.query.filter_by(id_empleado=current_user.id_usuario).order_by(Cita.fecha_hora).all()
    return render_template('trabajar_citas.html', citas=citas)

@bp.route('/confirmar_cita/<int:id_cita>', methods=['POST'])
@login_required
def confirmar_cita(id_cita):
    if current_user.rol != 'empleado':
        flash("Acceso denegado. Solo para empleados.", "danger")
        return redirect(url_for('auth.login'))
    cita = Cita.query.get_or_404(id_cita)
    if cita.id_empleado != current_user.id_usuario:
        flash("No tienes permiso para confirmar esta cita.", "danger")
        return redirect(url_for('employee.trabajar_citas'))
    if cita.estado != 'pendiente':
        flash("Esta cita no puede ser confirmada.", "danger")
        return redirect(url_for('employee.trabajar_citas'))
    cita.estado = 'confirmada'
    db.session.commit()
    flash("Cita confirmada con éxito.", "success")
    return redirect(url_for('employee.trabajar_citas'))

@bp.route('/completar_cita/<int:id_cita>', methods=['POST'])
@login_required
def completar_cita(id_cita):
    if current_user.rol != 'empleado':
        flash("Acceso denegado. Solo para empleados.", "danger")
        return redirect(url_for('auth.login'))
    cita = Cita.query.get_or_404(id_cita)
    if cita.id_empleado != current_user.id_usuario:
        flash("No tienes permiso para completar esta cita.", "danger")
        return redirect(url_for('employee.trabajar_citas'))
    if cita.estado != 'confirmada':
        flash("Esta cita no puede ser completada. Debe estar confirmada primero.", "danger")
        return redirect(url_for('employee.trabajar_citas'))
    
    cita.estado = 'completada'
    db.session.commit()

    return redirect(url_for('employee.generar_factura', id_cita=id_cita))

@bp.route('/generar_factura/<int:id_cita>')
@login_required
def generar_factura(id_cita):
    if current_user.rol != 'empleado':
        flash("Acceso denegado. Solo para empleados.", "danger")
        return redirect(url_for('auth.login'))
    
    cita = Cita.query.get_or_404(id_cita)
    if cita.estado != 'completada':
        flash("La cita debe estar completada para generar una factura.", "danger")
        return redirect(url_for('employee.trabajar_citas'))
    if cita.id_empleado != current_user.id_usuario:
        flash("No tienes permiso para generar esta factura.", "danger")
        return redirect(url_for('employee.trabajar_citas'))

    if not cita.id_usuario:
        flash("No se encontró un cliente asociado a esta cita.", "danger")
        return redirect(url_for('employee.trabajar_citas'))
    
    cliente = Usuario.query.get(cita.id_usuario)
    if not cliente:
        flash(f"No se encontró un usuario con ID {cita.id_usuario} asociado a la cita.", "danger")
        return redirect(url_for('employee.trabajar_citas'))
    
    logger.debug(f"Generando factura para cita {id_cita}. Cliente: {cliente.nombre}, ID Usuario: {cita.id_usuario}")

    servicio = Servicio.query.get(cita.id_servicio)
    if not servicio or not hasattr(servicio, 'precio') or servicio.precio is None:
        flash("El servicio asociado a la cita no tiene precio definido.", "danger")
        return redirect(url_for('employee.trabajar_citas'))

    subtotal = Decimal(str(servicio.precio))
    iva = subtotal * IVA_RATE
    total = subtotal + iva

    venta = Venta(id_usuario=cita.id_usuario, fecha_venta=datetime.utcnow(), total=total)
    db.session.add(venta)
    db.session.flush()

    detalle_venta = DetalleVenta(
        id_venta=venta.id_venta,
        id_servicio=cita.id_servicio,
        cantidad=1,
        precio_unitario=servicio.precio
    )
    db.session.add(detalle_venta)

    pago = Pago(id_venta=venta.id_venta, metodo_pago='efectivo', monto=total)
    db.session.add(pago)

    db.session.commit()

    nombre_archivo = f'factura_{cita.id_usuario}_{venta.id_venta}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    ruta_archivo = os.path.join(os.path.dirname(__file__), '..', 'static', nombre_archivo)
    c = canvas.Canvas(ruta_archivo, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)

    logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'casa-bella-logo.jpeg')
    if os.path.exists(logo_path):
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
    c.drawString(50, 645, f"Nombre: {cliente.nombre}")
    c.drawString(50, 630, f"Email: {cliente.email or 'No proporcionado'}")
    c.drawString(50, 615, f"Teléfono: {cliente.telefono or 'No proporcionado'}")

    y = 580
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "SERVICIOS:")
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.line(50, y-5, 550, y-5)
    
    y -= 25
    c.setFont("Helvetica", 9)
    subtotal_item = Decimal(str(1)) * Decimal(str(servicio.precio))
    c.drawString(60, y, f"{servicio.nombre} x 1 - ${subtotal_item.quantize(Decimal('0.01'))}")
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

    flash("Factura generada con éxito. Descargando...", "success")
    response = send_file(ruta_archivo, as_attachment=True, download_name=nombre_archivo)
    if os.path.exists(ruta_archivo):
        os.remove(ruta_archivo)
    return response

@bp.route('/generar_factura_manual', methods=['GET', 'POST'])
@login_required
def generar_factura_manual():
    if current_user.rol != 'empleado':
        flash("Acceso denegado. Solo para empleados.", "danger")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nombre_cliente = request.form.get('nombre_cliente')
        email_cliente = request.form.get('email_cliente')
        telefono_cliente = request.form.get('telefono_cliente')
        items = request.form.getlist('items[]')
        cantidades = request.form.getlist('cantidades[]')

        if not nombre_cliente:
            flash("Debe ingresar el nombre del cliente.", "danger")
            return redirect(url_for('employee.generar_factura_manual'))

        subtotal = Decimal('0.00')
        detalles_venta = []
        for item_id, cantidad in zip(items, cantidades):
            if item_id and cantidad:
                cantidad = int(cantidad)
                if cantidad <= 0:
                    flash(f"La cantidad para el item {item_id} debe ser mayor a 0.", "danger")
                    return redirect(url_for('employee.generar_factura_manual'))
                
                producto = Producto.query.get(item_id)
                servicio = Servicio.query.get(item_id) if not producto else None
                if producto:
                    if not hasattr(producto, 'stock') or producto.stock < cantidad:
                        flash(f"Stock insuficiente para el producto {producto.nombre}.", "danger")
                        return redirect(url_for('employee.generar_factura_manual'))
                    subtotal += Decimal(str(cantidad)) * Decimal(str(producto.precio))
                    producto.stock -= cantidad
                    movimiento = InventarioMovimiento(
                        id_producto=item_id,
                        tipo_movimiento='salida',
                        cantidad=-cantidad,
                        motivo=f'Venta manual ID: {datetime.utcnow().strftime("%Y%m%d_%H%M%S")}'
                    )
                    db.session.add(movimiento)
                elif servicio:
                    subtotal += Decimal(str(cantidad)) * Decimal(str(servicio.precio))
                else:
                    flash(f"Item {item_id} no encontrado.", "danger")
                    return redirect(url_for('employee.generar_factura_manual'))
                
                detalles_venta.append({
                    'id': item_id,
                    'cantidad': cantidad,
                    'precio_unitario': producto.precio if producto else servicio.precio,
                    'es_producto': bool(producto)
                })

        iva = subtotal * IVA_RATE
        total = subtotal + iva

        logger.debug(f"Creando venta: id_usuario=None, total={total}")

        try:
            venta = Venta(id_usuario=None, fecha_venta=datetime.utcnow(), total=total)
            db.session.add(venta)
            db.session.flush()
            logger.debug(f"Venta creada con ID: {venta.id_venta}")
        except Exception as e:
            logger.error(f"Error al crear venta: {str(e)} - Datos: id_usuario={None}, total={total}")
            flash("Error al guardar la venta. Contacte al administrador.", "danger")
            db.session.rollback()
            return redirect(url_for('employee.generar_factura_manual'))

        for detalle in detalles_venta:
            detalle_venta = DetalleVenta(
                id_venta=venta.id_venta,
                id_producto=detalle['id'] if detalle['es_producto'] else None,
                id_servicio=detalle['id'] if not detalle['es_producto'] else None,
                cantidad=detalle['cantidad'],
                precio_unitario=detalle['precio_unitario']
            )
            db.session.add(detalle_venta)

        pago = Pago(id_venta=venta.id_venta, metodo_pago='efectivo', monto=total)
        db.session.add(pago)
        db.session.commit()

        nombre_archivo = f'factura_manual_{venta.id_venta}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        ruta_archivo = os.path.join(os.path.dirname(__file__), '..', 'static', nombre_archivo)
        c = canvas.Canvas(ruta_archivo, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)

        logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'images', 'casa-bella-logo.jpeg')
        if os.path.exists(logo_path):
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
        c.drawString(50, 680, "FACTURA (Cliente No Registrado)")
        c.setFont("Helvetica", 10)
        c.drawString(400, 680, f"Fecha: {venta.fecha_venta.strftime('%Y-%m-%d %H:%M')}")
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, 660, "DATOS DEL CLIENTE:")
        c.setFont("Helvetica", 10)
        c.drawString(50, 645, f"Nombre: {nombre_cliente}")
        c.drawString(50, 630, f"Email: {email_cliente or 'No proporcionado'}")
        c.drawString(50, 615, f"Teléfono: {telefono_cliente or 'No proporcionado'}")

        y = 580
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "PRODUCTOS/SERVICIOS:")
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.line(50, y-5, 550, y-5)
        
        y -= 25
        c.setFont("Helvetica", 9)
        for detalle in detalles_venta:
            item_name = Producto.query.get(detalle['id']).nombre if detalle['es_producto'] else Servicio.query.get(detalle['id']).nombre
            subtotal_item = Decimal(str(detalle['cantidad'])) * Decimal(str(detalle['precio_unitario']))
            c.drawString(60, y, f"{item_name} x {detalle['cantidad']} - ${subtotal_item.quantize(Decimal('0.01'))}")
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

        flash("Factura generada con éxito. Descargando...", "success")
        response = send_file(ruta_archivo, as_attachment=True, download_name=nombre_archivo)
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)
        return response

    productos = Producto.query.all()
    servicios = Servicio.query.all()
    return render_template('generar_factura.html', productos=productos, servicios=servicios)