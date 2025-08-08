from app import db

class DetalleCarrito(db.Model):
    __tablename__ = 'detalle_carrito'
    id_detalle_carrito = db.Column(db.Integer, primary_key=True)
    id_carrito = db.Column(db.Integer, db.ForeignKey('carrito.id_carrito'))
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id_producto'))
    id_servicio = db.Column(db.Integer, db.ForeignKey('servicios.id_servicio'))
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
