from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///softwaresales.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat()
        }


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    products = db.relationship('Product', backref='category', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    version = db.Column(db.String(50))
    license_type = db.Column(db.String(50), default='perpetual')  # perpetual, subscription, trial
    download_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    stock = db.Column(db.Integer, default=-1)  # -1 = unlimited (digital)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'version': self.version,
            'license_type': self.license_type,
            'is_active': self.is_active,
            'stock': self.stock,
            'category_id': self.category_id,
            'category': self.category.to_dict() if self.category else None,
            'created_at': self.created_at.isoformat()
        }


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, paid, completed, cancelled
    total_amount = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)
    license_keys = db.relationship('LicenseKey', backref='order', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'user_id': self.user_id,
            'status': self.status,
            'total_amount': self.total_amount,
            'items': [item.to_dict() for item in self.items],
            'license_keys': [lk.to_dict() for lk in self.license_keys],
            'created_at': self.created_at.isoformat()
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'subtotal': self.quantity * self.unit_price
        }


class LicenseKey(db.Model):
    __tablename__ = 'license_keys'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)
    activated_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'product_id': self.product_id,
            'is_active': self.is_active,
            'activated_at': self.activated_at.isoformat() if self.activated_at else None
        }


class Cart(db.Model):
    __tablename__ = 'carts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    items = db.relationship('CartItem', backref='cart', lazy=True, cascade='all, delete-orphan')

    def total(self):
        return sum(item.product.price * item.quantity for item in self.items if item.product)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'items': [item.to_dict() for item in self.items],
            'total': self.total()
        }


class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('carts.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product': self.product.to_dict() if self.product else None,
            'quantity': self.quantity,
            'subtotal': self.product.price * self.quantity if self.product else 0
        }


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)


def require_auth(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user():
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


def generate_order_number():
    return 'ORD-' + uuid.uuid4().hex[:10].upper()


def generate_license_key():
    parts = [uuid.uuid4().hex[:8].upper() for _ in range(4)]
    return '-'.join(parts)


# ─────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['username', 'email', 'password']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Field {field} is required'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409

    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()

    cart = Cart(user_id=user.id)
    db.session.add(cart)
    db.session.commit()

    return jsonify({'message': 'User registered successfully', 'user': user.to_dict()}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    user = User.query.filter_by(email=data.get('email')).first()
    if not user or not user.check_password(data.get('password', '')):
        return jsonify({'error': 'Invalid credentials'}), 401

    session['user_id'] = user.id
    return jsonify({'message': 'Login successful', 'user': user.to_dict()})


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'})


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def me():
    return jsonify(get_current_user().to_dict())


# ─────────────────────────────────────────
# CATEGORY ROUTES
# ─────────────────────────────────────────

@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    return jsonify([c.to_dict() for c in categories])


@app.route('/api/categories', methods=['POST'])
@require_admin
def create_category():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'Category name is required'}), 400

    if Category.query.filter_by(name=data['name']).first():
        return jsonify({'error': 'Category already exists'}), 409

    category = Category(name=data['name'], description=data.get('description'))
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201


@app.route('/api/categories/<int:cat_id>', methods=['PUT'])
@require_admin
def update_category(cat_id):
    category = Category.query.get_or_404(cat_id)
    data = request.get_json()
    if data.get('name'):
        category.name = data['name']
    if 'description' in data:
        category.description = data['description']
    db.session.commit()
    return jsonify(category.to_dict())


@app.route('/api/categories/<int:cat_id>', methods=['DELETE'])
@require_admin
def delete_category(cat_id):
    category = Category.query.get_or_404(cat_id)
    db.session.delete(category)
    db.session.commit()
    return jsonify({'message': 'Category deleted'})


# ─────────────────────────────────────────
# PRODUCT ROUTES
# ─────────────────────────────────────────

@app.route('/api/products', methods=['GET'])
def get_products():
    query = Product.query.filter_by(is_active=True)
    category_id = request.args.get('category_id')
    search = request.args.get('search')
    if category_id:
        query = query.filter_by(category_id=int(category_id))
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    products = query.all()
    return jsonify([p.to_dict() for p in products])


@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict())


@app.route('/api/products', methods=['POST'])
@require_admin
def create_product():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['name', 'price']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Field {field} is required'}), 400

    product = Product(
        name=data['name'],
        description=data.get('description'),
        price=float(data['price']),
        version=data.get('version'),
        license_type=data.get('license_type', 'perpetual'),
        download_url=data.get('download_url'),
        is_active=data.get('is_active', True),
        stock=data.get('stock', -1),
        category_id=data.get('category_id')
    )
    db.session.add(product)
    db.session.commit()
    return jsonify(product.to_dict()), 201


@app.route('/api/products/<int:product_id>', methods=['PUT'])
@require_admin
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json()
    fields = ['name', 'description', 'price', 'version', 'license_type',
              'download_url', 'is_active', 'stock', 'category_id']
    for field in fields:
        if field in data:
            setattr(product, field, data[field])
    db.session.commit()
    return jsonify(product.to_dict())


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@require_admin
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = False
    db.session.commit()
    return jsonify({'message': 'Product deactivated'})


# ─────────────────────────────────────────
# CART ROUTES
# ─────────────────────────────────────────

@app.route('/api/cart', methods=['GET'])
@require_auth
def get_cart():
    user = get_current_user()
    cart = Cart.query.filter_by(user_id=user.id).first()
    if not cart:
        cart = Cart(user_id=user.id)
        db.session.add(cart)
        db.session.commit()
    return jsonify(cart.to_dict())


@app.route('/api/cart/items', methods=['POST'])
@require_auth
def add_to_cart():
    user = get_current_user()
    data = request.get_json()
    if not data or not data.get('product_id'):
        return jsonify({'error': 'product_id is required'}), 400

    product = Product.query.get(data['product_id'])
    if not product or not product.is_active:
        return jsonify({'error': 'Product not found'}), 404

    cart = Cart.query.filter_by(user_id=user.id).first()
    if not cart:
        cart = Cart(user_id=user.id)
        db.session.add(cart)
        db.session.flush()

    quantity = int(data.get('quantity', 1))
    existing = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
    if existing:
        existing.quantity += quantity
    else:
        item = CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity)
        db.session.add(item)

    db.session.commit()
    return jsonify(cart.to_dict())


@app.route('/api/cart/items/<int:item_id>', methods=['PUT'])
@require_auth
def update_cart_item(item_id):
    user = get_current_user()
    cart = Cart.query.filter_by(user_id=user.id).first()
    if not cart:
        return jsonify({'error': 'Cart not found'}), 404

    item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    data = request.get_json()
    quantity = int(data.get('quantity', 1))
    if quantity <= 0:
        db.session.delete(item)
    else:
        item.quantity = quantity
    db.session.commit()
    return jsonify(cart.to_dict())


@app.route('/api/cart/items/<int:item_id>', methods=['DELETE'])
@require_auth
def remove_from_cart(item_id):
    user = get_current_user()
    cart = Cart.query.filter_by(user_id=user.id).first()
    if not cart:
        return jsonify({'error': 'Cart not found'}), 404

    item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify(cart.to_dict())


@app.route('/api/cart/clear', methods=['DELETE'])
@require_auth
def clear_cart():
    user = get_current_user()
    cart = Cart.query.filter_by(user_id=user.id).first()
    if cart:
        CartItem.query.filter_by(cart_id=cart.id).delete()
        db.session.commit()
    return jsonify({'message': 'Cart cleared'})


# ─────────────────────────────────────────
# ORDER ROUTES
# ─────────────────────────────────────────

@app.route('/api/orders', methods=['POST'])
@require_auth
def create_order():
    user = get_current_user()
    cart = Cart.query.filter_by(user_id=user.id).first()

    if not cart or not cart.items:
        return jsonify({'error': 'Cart is empty'}), 400

    order = Order(
        order_number=generate_order_number(),
        user_id=user.id,
        status='pending',
        total_amount=cart.total()
    )
    db.session.add(order)
    db.session.flush()

    for cart_item in cart.items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            unit_price=cart_item.product.price
        )
        db.session.add(order_item)

    CartItem.query.filter_by(cart_id=cart.id).delete()
    db.session.commit()
    return jsonify(order.to_dict()), 201


@app.route('/api/orders', methods=['GET'])
@require_auth
def get_orders():
    user = get_current_user()
    if user.is_admin:
        orders = Order.query.order_by(Order.created_at.desc()).all()
    else:
        orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders])


@app.route('/api/orders/<int:order_id>', methods=['GET'])
@require_auth
def get_order(order_id):
    user = get_current_user()
    order = Order.query.get_or_404(order_id)
    if not user.is_admin and order.user_id != user.id:
        return jsonify({'error': 'Access denied'}), 403
    return jsonify(order.to_dict())


@app.route('/api/orders/<int:order_id>/pay', methods=['POST'])
@require_auth
def pay_order(order_id):
    user = get_current_user()
    order = Order.query.get_or_404(order_id)
    if order.user_id != user.id:
        return jsonify({'error': 'Access denied'}), 403
    if order.status != 'pending':
        return jsonify({'error': f'Order is already {order.status}'}), 400

    # Simulate payment processing
    order.status = 'paid'
    order.updated_at = datetime.utcnow()

    # Generate license keys for each item
    for item in order.items:
        for _ in range(item.quantity):
            lk = LicenseKey(
                key=generate_license_key(),
                product_id=item.product_id,
                order_id=order.id,
                user_id=user.id,
                is_active=True,
                activated_at=datetime.utcnow()
            )
            db.session.add(lk)

    order.status = 'completed'
    db.session.commit()
    return jsonify(order.to_dict())


@app.route('/api/orders/<int:order_id>/cancel', methods=['POST'])
@require_auth
def cancel_order(order_id):
    user = get_current_user()
    order = Order.query.get_or_404(order_id)
    if not user.is_admin and order.user_id != user.id:
        return jsonify({'error': 'Access denied'}), 403
    if order.status not in ('pending',):
        return jsonify({'error': 'Only pending orders can be cancelled'}), 400
    order.status = 'cancelled'
    order.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(order.to_dict())


# ─────────────────────────────────────────
# LICENSE KEY ROUTES
# ─────────────────────────────────────────

@app.route('/api/licenses', methods=['GET'])
@require_auth
def get_licenses():
    user = get_current_user()
    if user.is_admin:
        licenses = LicenseKey.query.all()
    else:
        licenses = LicenseKey.query.filter_by(user_id=user.id).all()
    return jsonify([lk.to_dict() for lk in licenses])


@app.route('/api/licenses/validate', methods=['POST'])
def validate_license():
    data = request.get_json()
    key = data.get('key') if data else None
    if not key:
        return jsonify({'error': 'License key is required'}), 400

    lk = LicenseKey.query.filter_by(key=key).first()
    if not lk:
        return jsonify({'valid': False, 'message': 'License key not found'}), 404

    return jsonify({
        'valid': lk.is_active,
        'product_id': lk.product_id,
        'activated_at': lk.activated_at.isoformat() if lk.activated_at else None
    })


# ─────────────────────────────────────────
# ADMIN STATS
# ─────────────────────────────────────────

@app.route('/api/admin/stats', methods=['GET'])
@require_admin
def admin_stats():
    total_users = User.query.count()
    total_products = Product.query.filter_by(is_active=True).count()
    total_orders = Order.query.count()
    completed_orders = Order.query.filter_by(status='completed').count()
    total_revenue = db.session.query(
        db.func.sum(Order.total_amount)
    ).filter_by(status='completed').scalar() or 0.0

    return jsonify({
        'total_users': total_users,
        'total_products': total_products,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'total_revenue': total_revenue
    })


# ─────────────────────────────────────────
# INIT & SEED
# ─────────────────────────────────────────

def seed_data():
    if User.query.count() == 0:
        admin = User(username='admin', email='admin@softwaresales.com', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.flush()
        cart = Cart(user_id=admin.id)
        db.session.add(cart)

        cat1 = Category(name='Productivity', description='Productivity software tools')
        cat2 = Category(name='Security', description='Security and antivirus software')
        cat3 = Category(name='Development', description='Developer tools and IDEs')
        db.session.add_all([cat1, cat2, cat3])
        db.session.flush()

        products = [
            Product(name='OfficeMax Pro', description='Complete office suite', price=99.99,
                    version='2024', license_type='perpetual', category_id=cat1.id),
            Product(name='SecureShield', description='Advanced antivirus protection', price=49.99,
                    version='5.2', license_type='subscription', category_id=cat2.id),
            Product(name='DevStudio Ultimate', description='Powerful IDE for developers', price=199.99,
                    version='3.0', license_type='perpetual', category_id=cat3.id),
            Product(name='TaskFlow', description='Project management tool', price=29.99,
                    version='1.5', license_type='subscription', category_id=cat1.id),
        ]
        db.session.add_all(products)
        db.session.commit()
        print('[seed] Admin user and sample data created.')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True, host='0.0.0.0', port=5000)