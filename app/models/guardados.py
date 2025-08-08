from app import db

class Guardado(db.Model):
    __tablename__ = 'guardados'
    id_guardado = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'))
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id_producto'))
    id_servicio = db.Column(db.Integer, db.ForeignKey('servicios.id_servicio'))
    fecha_guardado = db.Column(db.DateTime, default=db.func.current_timestamp())
