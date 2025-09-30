from sqlalchemy import Enum
from app import db

class Notificacion(db.Model):
    __tablename__ = 'notificaciones'
    id_notificacion = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))
    mensaje = db.Column(db.Text, nullable=False)
    tipo = db.Column(Enum('cita', 'promocion', 'inventario', name='tipo_notificacion_enum'), nullable=False)
    fecha_envio = db.Column(db.DateTime, default=db.func.current_timestamp())
    leida = db.Column(db.Boolean, default=False)