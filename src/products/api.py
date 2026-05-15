from flask import Flask, jsonify, request
from .models import Product

app = Flask(__name__)

@app.route('/products', methods=['GET'])
def get_products():
    """
    Retrieves all products.
    """
    products = Product.query.all()
    product_list = [dict(product) for product in products]
    return jsonify(product_list)

@app.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """
    Retrieves a single product by ID.
    """
    product = Product.query.get(product_id)
    if product:
        return jsonify(product)
    else:
        return jsonify({'message': 'Product not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
```
```python
# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(100))
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Product {self.name}>'