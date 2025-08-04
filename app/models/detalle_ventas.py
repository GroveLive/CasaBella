
from app import db

class DetalleVenta(db.Model):
    __tablename__ = 'detalle_ventas'
    id_detalle = db.Column(db.Integer, primary_key=True)
    id_venta = db.Column(db.Integer, db.ForeignKey('ventas.id_venta'))
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id_producto'))
    id_servicio = db.Column(db.Integer, db.ForeignKey('servicios.id_servicio'))
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
