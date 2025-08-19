from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models.citas import Cita
from flask_login import login_required, current_user
import logging
from datetime import datetime

bp = Blueprint('employee', __name__, url_prefix='/employee')

# Configurar logging básico
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
    flash("Cita completada con éxito.", "success")
    return redirect(url_for('employee.trabajar_citas'))