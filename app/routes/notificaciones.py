# app/routes/notificaciones.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.notificaciones import Notificacion

bp = Blueprint('notificaciones', __name__, url_prefix='/notificaciones')

@bp.route('/dashboard')
@login_required
def notificaciones_dashboard():
    """Muestra la lista de notificaciones del usuario autenticado."""
    # Obtener notificaciones del usuario actual
    notificaciones = Notificacion.query.filter_by(id_usuario=current_user.id_usuario).order_by(Notificacion.fecha_envio.desc()).all()
    
    # Marcar como leídas si se solicita (por ejemplo, al cargar la página)
    if request.args.get('mark_as_read'):
        notificaciones_a_marcar = Notificacion.query.filter_by(id_usuario=current_user.id_usuario, leida=False).all()
        for notificacion in notificaciones_a_marcar:
            notificacion.leida = True
        db.session.commit()
    
    return render_template('notificaciones.html', notificaciones=notificaciones)

@bp.route('/mark/<int:id_notificacion>', methods=['POST'])
@login_required
def marcar_leida(id_notificacion):
    """Marca una notificación específica como leída."""
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'Debes iniciar sesión.'}), 403
    
    notificacion = Notificacion.query.get_or_404(id_notificacion)
    if notificacion.id_usuario != current_user.id_usuario:
        return jsonify({'success': False, 'message': 'No tienes permiso para marcar esta notificación.'}), 403
    
    notificacion.leida = True
    db.session.commit()
    return jsonify({'success': True, 'message': 'Notificación marcada como leída.'})

@bp.route('/eliminar/<int:id_notificacion>', methods=['POST'])
@login_required
def eliminar(id_notificacion):
    """Elimina una notificación específica."""
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'Debes iniciar sesión.'}), 403
    
    notificacion = Notificacion.query.get_or_404(id_notificacion)
    if notificacion.id_usuario != current_user.id_usuario:
        return jsonify({'success': False, 'message': 'No tienes permiso para eliminar esta notificación.'}), 403
    
    try:
        db.session.delete(notificacion)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Notificación eliminada con éxito.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al eliminar: {str(e)}'}), 500