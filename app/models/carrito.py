
from app import db

class Carrito(db.Model):
    __tablename__ = 'carrito'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    fecha_agregado = db.Column(db.DateTime, default=db.func.now())

    usuario = db.relationship('Usuario', backref=db.backref('carrito_items', lazy=True))
    producto = db.relationship('Producto', backref=db.backref('carrito_items', lazy=True))

    def __repr__(self):
        return f'<Carrito {self.id} - {self.producto.nombre} x{self.cantidad}>'
