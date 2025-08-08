
from app import db

class Promocion(db.Model):
    __tablename__ = 'promociones'
    id_promocion = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    descuento = db.Column(db.Numeric(10, 2))
    fecha_inicio = db.Column(db.DateTime, nullable=False)
    fecha_fin = db.Column(db.DateTime, nullable=False)
    id_servicio = db.Column(db.Integer, db.ForeignKey('servicios.id_servicio'))
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id_producto'))

