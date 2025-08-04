
from app import db

class Asignacion(db.Model):
    __tablename__ = 'asignaciones'
    id_asignacion = db.Column(db.Integer, primary_key=True)
    id_cita = db.Column(db.Integer, db.ForeignKey('citas.id_cita'))
    id_empleado = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))
    fecha_asignacion = db.Column(db.DateTime, default=db.func.current_timestamp())
    notas = db.Column(db.Text)