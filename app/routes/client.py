from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file
from app import db
from app.models.servicios import Servicio
from app.models.productos import Producto
from app.models.citas import Cita
from app.models.carrito import Carrito
from app.models.detalle_carrito import DetalleCarrito
from app.models.ventas import Venta
from app.models.detalle_ventas import DetalleVenta
from flask_login import login_required, current_user
import logging
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from sqlalchemy.orm import joinedload
import os
import subprocess

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
    if detalle.carrito.id_usuario != current_user.id_usuario:
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
                producto = detalle.producto
                producto.stock -= detalle.cantidad
                if producto.stock < 0:
                    db.session.rollback()
                    flash("Stock insuficiente para procesar la compra.", "danger")
                    return redirect(url_for('client.carrito'))
            # Crear la venta
            total = sum(d.cantidad * d.precio_unitario for d in carrito.detalles)
            venta = Venta(id_usuario=current_user.id_usuario, fecha_venta=datetime.utcnow(), total=total)
            db.session.add(venta)
            db.session.commit()

            # Crear detalles de venta basados en el carrito
            for detalle in carrito.detalles:
                detalle_venta = DetalleVenta(
                    id_venta=venta.id_venta,
                    id_producto=detalle.id_producto,
                    id_servicio=detalle.id_servicio if detalle.id_servicio else None,
                    cantidad=detalle.cantidad,
                    precio_unitario=detalle.precio_unitario
                )
                db.session.add(detalle_venta)

            # Actualizar estado del carrito y eliminar detalles
            carrito.estado = 'completado'
            for detalle in carrito.detalles:
                db.session.delete(detalle)
            db.session.commit()

            # Generar factura en LaTeX
            latex_content = generate_factura_latex(carrito, venta)
            with open('factura.tex', 'w') as f:
                f.write(latex_content)
            # Verificar si latexmk está disponible
            if subprocess.run(['which', 'latexmk'], capture_output=True, text=True).returncode != 0:
                logger.error("latexmk no está instalado o no está en el PATH")
                raise Exception("latexmk no está instalado. Instala TeX Live con 'sudo apt install texlive-full'.")
            # Capturar la salida de latexmk
            result = subprocess.run(['latexmk', '-pdf', 'factura.tex'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Error al ejecutar latexmk. Salida: {result.stderr}")
                with open('factura.tex', 'r') as f:
                    logger.error(f"Contenido de factura.tex: {f.read()}")
                raise Exception("Fallo al generar el PDF con LaTeX")
            # Enviar el PDF como descarga
            from flask import send_file
            flash("Compra procesada con éxito. Descargando factura...", "success")
            response = send_file('factura.pdf', as_attachment=True, attachment_filename=f'factura_{current_user.id_usuario}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')
            # Eliminar archivos temporales después de enviar
            for file in ['factura.tex', 'factura.log', 'factura.aux', 'factura.pdf']:
                if os.path.exists(file):
                    os.remove(file)
            return response
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al procesar la compra: {str(e)}")
            flash(f"Ocurrió un error al procesar la compra: {str(e)}. Por favor, intenta de nuevo.", "danger")
            return redirect(url_for('client.carrito'))
    return render_template('procesar_compra.html', carrito=carrito)

# Función auxiliar para generar el contenido LaTeX de la factura
def generate_factura_latex(carrito, venta):
    detalles = carrito.detalles
    total = sum(d.cantidad * d.precio_unitario for d in detalles)
    # Construir las líneas de la tabla dinámicamente
    table_rows = []
    for detalle in detalles:
        row = f"{detalle.producto.nombre} & {detalle.cantidad} & ${detalle.precio_unitario:.2f} & ${detalle.cantidad * detalle.precio_unitario:.2f} \\\\"
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
Fecha: {venta.fecha_venta.strftime('%Y-%m-%d %H:%M')} \\\\
Cliente: {current_user.nombre} (ID: {current_user.id_usuario}) \\\\
\\end{{center}}

\\begin{{longtable}}{{lccr}}
\\toprule
Producto & Cantidad & Precio Unitario & Subtotal \\\\
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
    if not servicio_id or not fecha_hora:
        flash("Error al reservar la cita. Completa todos los campos.", "danger")
        return redirect(url_for('client.citas'))
    try:
        servicio_id = int(servicio_id)
        servicio = Servicio.query.get(servicio_id)
        if not servicio:
            flash("Servicio no encontrado.", "danger")
            return redirect(url_for('client.citas'))
        fecha_hora = fecha_hora.replace('T', ' ')
        fecha_hora = datetime.strptime(fecha_hora, '%Y-%m-%d %H:%M')
        cita = Cita(id_usuario=current_user.id_usuario, id_servicio=servicio_id, fecha_hora=fecha_hora, estado='pendiente', id_empleado=None)
        db.session.add(cita)
        db.session.commit()
        flash("Cita reservada con éxito. Te contactaremos para confirmación.", "success")
    except ValueError as e:
        logger.error(f"Error de formato en fecha_hora: {str(e)}")
        flash("Error: Formato de fecha inválido. Usa YYYY-MM-DD HH:MM.", "danger")
    except Exception as e:
        logger.error(f"Error al reservar cita: {str(e)}")
        flash("Ocurrió un error al reservar la cita. Por favor, intenta de nuevo.", "danger")
    return redirect(url_for('client.citas'))