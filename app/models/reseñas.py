from app import db

class Reseña(db.Model):
    __tablename__ = 'reseñas'
    id_resena = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))
    id_servicio = db.Column(db.Integer, db.ForeignKey('servicios.id_servicio'))
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id_producto'))
    calificacion = db.Column(db.Integer, nullable=False)
    comentario = db.Column(db.Text)
    fecha_resena = db.Column(db.DateTime, default=db.func.current_timestamp())
