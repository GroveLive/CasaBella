from sqlalchemy import Enum
from app import db

class Cita(db.Model):
    __tablename__ = 'citas'
    id_cita = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))  # Cliente
    id_empleado = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))  # Empleado
    id_servicio = db.Column(db.Integer, db.ForeignKey('servicios.id_servicio'))
    fecha_hora = db.Column(db.DateTime, nullable=False)
    estado = db.Column(Enum('pendiente', 'confirmada', 'cancelada', 'completada', name='estado_enum'), default='pendiente')
    notas = db.Column(db.Text)

    # Relaciones usando cadenas
    asignaciones = db.relationship('Asignacion', backref='cita', lazy=True)
