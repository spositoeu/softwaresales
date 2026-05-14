import os
import uuid
import hmac
import hashlib
import secrets
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from functools import wraps
from typing import Optional, List, Dict, Any

import jwt
from flask import Flask, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Numeric, Enum as SAEnum
from werkzeug.security import generate_password_hash, check_password_hash
from marshmallow import Schema, fields, validate, ValidationError, validates_schema

# ---------------------------------------------------------------------------
# App & Config
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///softwaresales.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
app.config["JWT_ACCESS_EXPIRE_MINUTES"] = int(os.getenv("JWT_ACCESS_EXPIRE_MINUTES", "60"))
app.config["JWT_REFRESH_EXPIRE_DAYS"] = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "30"))
app.config["STRIPE_SECRET_KEY"] = os.getenv("STRIPE_SECRET_KEY", "")
app.config["STRIPE_WEBHOOK_SECRET"] = os.getenv("STRIPE_WEBHOOK_SECRET", "")

db = SQLAlchemy(app)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Role(str, Enum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"


class ProductType(str, Enum):
    LICENSE = "LICENSE"
    SUBSCRIPTION = "SUBSCRIPTION"
    DOWNLOAD = "DOWNLOAD"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.CUSTOMER.value)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    orders = db.relationship("Order", back_populates="user", lazy="dynamic")
    licenses = db.relationship("License", back_populates="user", lazy="dynamic")
    refresh_tokens = db.relationship("RefreshToken", back_populates="user", lazy="dynamic")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "createdAt": self.created_at.isoformat(),
        }


class RefreshToken(db.Model):
    __tablename__ = "refresh_tokens"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token = db.Column(db.String(512), unique=True, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", back_populates="refresh_tokens")


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    price = db.Column(Numeric(10, 2), nullable=False)
    product_type = db.Column(db.String(20), nullable=False, default=ProductType.LICENSE.value)
    download_url = db.Column(db.String(1024), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    order_items = db.relationship("OrderItem", back_populates="product")
    licenses = db.relationship("License", back_populates="product")

    def to_dict(self, admin: bool = False) -> dict:
        data = {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "price": str(self.price),
            "type": self.product_type,
            "isActive": self.is_active,
            "createdAt": self.created_at.isoformat(),
        }
        if admin:
            data["downloadUrl"] = self.download_url
        return data


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=OrderStatus.PENDING.value)
    total_amount = db.Column(Numeric(10, 2), nullable=False)
    stripe_payment_intent_id = db.Column(db.String(255), nullable=True, unique=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    licenses = db.relationship("License", back_populates="order")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "status": self.status,
            "totalAmount": str(self.total_amount),
            "stripePaymentIntentId": self.stripe_payment_intent_id,
            "createdAt": self.created_at.isoformat(),
            "items": [item.to_dict() for item in self.items],
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = db.Column(db.String(36), db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(Numeric(10, 2), nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "productId": self.product_id,
            "productName": self.product.name if self.product else None,
            "quantity": self.quantity,
            "unitPrice": str(self.unit_price),
        }


class License(db.Model):
    __tablename__ = "licenses"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = db.Column(db.String(255), unique=True, nullable=False, default=lambda: str(uuid.uuid4()).upper())
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey("products.id"), nullable=False)
    order_id = db.Column(db.String(36), db.ForeignKey("orders.id"), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", back_populates="licenses")
    product = db.relationship("Product", back_populates="licenses")
    order = db.relationship("Order", back_populates="licenses")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "key": self.key,
            "productId": self.product_id,
            "productName": self.product.name if self.product else None,
            "orderId": self.order_id,
            "expiresAt": self.expires_at.isoformat() if self.expires_at else None,
            "isActive": self.is_active,
            "createdAt": self.created_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# Schemas (Marshmallow validation)
# ---------------------------------------------------------------------------

class RegisterSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128))


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)


class RefreshSchema(Schema):
    refreshToken = fields.Str(required=True)


class ProductCreateSchema(Schema):
    slug = fields.Str(required=True, validate=validate.Length(min=2, max=255))
    name = fields.Str(required=True, validate=validate.Length(min=2, max=255))
    description = fields.Str(load_default="")
    price = fields.Decimal(required=True, places=2)
    type = fields.Str(required=True, validate=validate.OneOf([t.value for t in ProductType]))
    downloadUrl = fields.Str(load_default=None, allow_none=True)
    isActive = fields.Bool(load_default=True)


class ProductUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=2, max=255))
    description = fields.Str()
    price = fields.Decimal(places=2)
    type = fields.Str(validate=validate.OneOf([t.value for t in ProductType]))
    downloadUrl = fields.Str(allow_none=True)
    isActive = fields.Bool()


class OrderItemSchema(Schema):
    productId = fields.Str(required=True)
    quantity = fields.Int(required=True, validate=validate.Range(min=1, max=100))


class OrderCreateSchema(Schema):
    items = fields.List(fields.Nested(OrderItemSchema), required=True, validate=validate.Length(min=1))


class PaymentIntentSchema(Schema):
    orderId = fields.Str(required=True)


# ---------------------------------------------------------------------------
# Auth utilities
# ---------------------------------------------------------------------------

def generate_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=app.config["JWT_ACCESS_EXPIRE_MINUTES"]
    )
    payload = {"sub": user_id, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


def generate_refresh_token_str() -> str:
    return secrets.token_urlsafe(64)


def save_refresh_token(user_id: str, token_str: str) -> RefreshToken:
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=app.config["JWT_REFRESH_EXPIRE_DAYS"]
    )
    rt = RefreshToken(token=token_str, user_id=user_id, expires_at=expires_at)
    db.session.add(rt)
    db.session.commit()
    return rt


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])


# ---------------------------------------------------------------------------
# Middleware / decorators
# ---------------------------------------------------------------------------

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth_header[7:]
        try:
            payload = decode_access_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        if payload.get("type") != "access":
            return jsonify({"error": "Invalid token type"}), 401
        user = db.session.get(User, payload["sub"])
        if not user or not user.is_active or user.deleted_at:
            return jsonify({"error": "User not found or inactive"}), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if g.current_user.role != Role.ADMIN.value:
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


def validate_body(schema_class):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                data = schema_class().load(request.get_json(force=True, silent=True) or {})
            except ValidationError as err:
                return jsonify({"error": "Validation failed", "details": err.messages}), 422
            g.validated_data = data
            return f(*args, **kwargs)
        return decorated
    return decorator


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(e):
    logger.exception("Internal server error")
    return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Pagination helper
# ---------------------------------------------------------------------------

def paginate_query(query, page: int = 1, per_page: int = 20) -> dict:
    page = max(1, page)
    per_page = min(100, max(1, per_page))
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": items,
        "pagination": {
            "page": page,
            "perPage": per_page,
            "total": total,
            "totalPages": (total + per_page - 1) // per_page,
        },
    }


# ---------------------------------------------------------------------------
# AUTH routes  /api/v1/auth
# ---------------------------------------------------------------------------

@app.route("/api/v1/auth/register", methods=["POST"])
@validate_body(RegisterSchema)
def auth_register():
    data = g.validated_data
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409
    user = User(email=data["email"])
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    access_token = generate_access_token(user.id, user.role)
    refresh_token_str = generate_refresh_token_str()
    save_refresh_token(user.id, refresh_token_str)
    logger.info("User registered: %s", user.email)
    return jsonify({
        "user": user.to_dict(),
        "accessToken": access_token,
        "refreshToken": refresh_token_str,
    }), 201


@app.route("/api/v1/auth/login", methods=["POST"])
@validate_body(LoginSchema)
def auth_login():
    data = g.validated_data
    user = User.query.filter_by(email=data["email"]).first()
    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401
    if not user.is_active or user.deleted_at:
        return jsonify({"error": "Account disabled"}), 403
    access_token = generate_access_token(user.id, user.role)
    refresh_token_str = generate_refresh_token_str()
    save_refresh_token(user.id, refresh_token_str)
    logger.info("User logged in: %s", user.email)
    return jsonify({
        "user": user.to_dict(),
        "accessToken": access_token,
        "refreshToken": refresh_token_str,
    })


@app.route("/api/v1/auth/refresh", methods=["POST"])
@validate_body(RefreshSchema)
def auth_refresh():
    data = g.validated_data
    rt = RefreshToken.query.filter_by(token=data["refreshToken"], revoked=False).first()
    if not rt:
        return jsonify({"error": "Invalid refresh token"}), 401
    if rt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        rt.revoked = True
        db.session.commit()
        return jsonify({"error": "Refresh token expired"}), 401
    user = db.session.get(User, rt.user_id)
    if not user or not user.is_active:
        return jsonify({"error": "User not found"}), 401
    rt.revoked = True
    db.session.flush()
    access_token = generate_access_token(user.id, user.role)
    new_refresh_str = generate_refresh_token_str()
    save_refresh_token(user.id, new_refresh_str)
    return jsonify({"accessToken": access_token, "refreshToken": new_refresh_str})


@app.route("/api/v1/auth/logout", methods=["POST"])
@require_auth
def auth_logout():
    body = request.get_json(force=True, silent=True) or {}
    refresh_token_str = body.get("refreshToken")
    if refresh_token_str:
        rt = RefreshToken.query.filter_by(
            token=refresh_token_str, user_id=g.current_user.id
        ).first()
        if rt:
            rt.revoked = True
            db.session.commit()
    return jsonify({"message": "Logged out successfully"})


# ---------------------------------------------------------------------------
# PRODUCTS routes  /api/v1/products  +  /api/v1/admin/products
# ---------------------------------------------------------------------------

@app.route("/api/v1/products", methods=["GET"])
def products_list():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("perPage", 20, type=int)
    q = request.args.get("q", "")
    product_type = request.args.get("type", "")

    query = Product.query.filter_by(is_active=True).filter(Product.deleted_at.is_(None))
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    if product_type and product_type in [t.value for t in ProductType]:
        query = query.filter_by(product_type=product_type)
    query = query.order_by(Product.created_at.desc())

    result = paginate_query(query, page, per_page)
    return jsonify({
        "products": [p.to_dict() for p in result["items"]],
        "pagination": result["pagination"],
    })


@app.route("/api/v1/products/<slug>", methods=["GET"])
def products_detail(slug: str):
    product = Product.query.filter_by(slug=slug, is_active=True).filter(
        Product.deleted_at.is_(None)
    ).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify({"product": product.to_dict()})


@app.route("/api/v1/admin/products", methods=["POST"])
@require_admin
@validate_body(ProductCreateSchema)
def admin_products_create():
    data = g.validated_data
    if Product.query.filter_by(slug=data["slug"]).first():
        return jsonify({"error": "Slug already exists"}), 409
    product = Product(
        slug=data["slug"],
        name=data["name"],
        description=data.get("description", ""),
        price=data["price"],
        product_type=data["type"],
        download_url=data.get("downloadUrl"),
        is_active=data.get("isActive", True),
    )
    db.session.add(product)
    db.session.commit()
    logger.info("Product created: %s", product.slug)
    return jsonify({"product": product.to_dict(admin=True)}), 201


@app.route("/api/v1/admin/products/<product_id>", methods=["PUT"])
@require_admin
@validate_body(ProductUpdateSchema)
def admin_products_update(product_id: str):
    product = db.session.get(Product, product_id)
    if not product or product.deleted_at:
        return jsonify({"error": "Product not found"}), 404
    data = g.validated_data
    if "name" in data:
        product.name = data["name"]
    if "description" in data:
        product.description = data["description"]
    if "price" in data:
        product.price = data["price"]
    if "type" in data:
        product.product_type = data["type"]
    if "downloadUrl" in data:
        product.download_url = data["downloadUrl"]
    if "isActive" in data:
        product.is_active = data["isActive"]
    product.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"product": product.to_dict(admin=True)})


@app.route("/api/v1/admin/products/<product_id>", methods=["DELETE"])
@require_admin
def admin_products_delete(product_id: str):
    product = db.session.get(Product, product_id)
    if not product or product.deleted_at:
        return jsonify({"error": "Product not found"}), 404
    product.deleted_at = datetime.now(timezone.utc)
    product.is_active = False
    db.session.commit()
    logger.info("Product soft-deleted: %s", product_id)
    return jsonify({"message": "Product deleted"})


# ---------------------------------------------------------------------------
# ORDERS routes  /api/v1/orders
# ---------------------------------------------------------------------------

@app.route("/api/v1/orders", methods=["POST"])
@require_auth
@validate_body(OrderCreateSchema)
def orders_create():
    data = g.validated_data
    user = g.current_user
    items_data = data["items"]

    # Resolve products and calculate total
    resolved_items = []
    total = Decimal("0.00")
    for item in items_data:
        product = db.session.get(Product, item["productId"])
        if not product or not product.is_active or product.deleted_at:
            return jsonify({"error": f"Product {item['productId']} not found or inactive"}), 404
        line_total = Decimal(str(product.price)) * item["quantity"]
        total += line_total
        resolved_items.append({"product": product, "quantity": item["quantity"]})

    order = Order(user_id=user.id, total_amount=total)
    db.session.add(order)
    db.session.flush()

    for ri in resolved_items:
        oi = OrderItem(
            order_id=order.id,
            product_id=ri["product"].id,
            quantity=ri["quantity"],
            unit_price=ri["product"].price,
        )
        db.session.add(oi)

    db.session.commit()
    logger.info("Order created: %s by user %s", order.id, user.id)
    return jsonify({"order": order.to_dict()}), 201


@app.route("/api/v1/orders", methods=["GET"])
@require_auth
def orders_list():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("perPage", 20, type=int)
    user = g.current_user

    query = Order.query.filter_by(user_id=user.id).filter(
        Order.deleted_at.is_(None)
    ).order_by(Order.created_at.desc())

    result = paginate_query(query, page, per_page)
    return jsonify({
        "orders": [o.to_dict() for o in result["items"]],
        "pagination": result["pagination"],
    })


@app.route("/api/v1/orders/<order_id>", methods=["GET"])
@require_auth
def orders_detail(order_id: str):
    user = g.current_user
    order = db.session.get(Order, order_id)
    if not order or order.deleted_at:
        return jsonify({"error": "Order not found"}), 404
    # Customers can only view their own orders; admins see all
    if user.role != Role.ADMIN.value and order.user_id != user.id:
        return jsonify({"error": "Forbidden"}), 403
    return jsonify({"order": order.to_dict()})


# ---------------------------------------------------------------------------
# PAYMENTS routes  /api/v1/payments
# ---------------------------------------------------------------------------

def _get_stripe():
    try:
        import stripe as stripe_lib
        stripe_lib.api_key = app.config["STRIPE_SECRET_KEY"]
        return stripe_lib
    except ImportError:
        return None


@app.route("/api/v1/payments/intent", methods=["POST"])
@require_auth
@validate_body(PaymentIntentSchema)
def payments_create_intent():
    data = g.validated_data
    user = g.current_user
    order = db.session.get(Order, data["orderId"])

    if not order or order.deleted_at:
        return jsonify({"error": "Order not found"}), 404
    if order.user_id != user.id and user.role != Role.ADMIN.value:
        return jsonify({"error": "Forbidden"}), 403
    if order.status != OrderStatus.PENDING.value:
        return jsonify({"error": "Order is not in PENDING status"}), 409

    stripe = _get_stripe()
    if not stripe or not app.config["STRIPE_SECRET_KEY"]:
        # Return a mock intent when Stripe is not configured (dev mode)
        mock_intent_id = f"pi_mock_{uuid.uuid4().hex}"
        order.stripe_payment_intent_id = mock_intent_id
        db.session.commit()
        return jsonify({
            "clientSecret": f"{mock_intent_id}_secret_mock",
            "paymentIntentId": mock_intent_id,
            "amount": int(Decimal(str(order.total_amount)) * 100),
            "currency": "usd",
        })

    # Idempotency: reuse existing intent if present
    if order.stripe_payment_intent_id:
        try:
            intent = stripe.PaymentIntent.retrieve(order.stripe_payment_intent_id)
            return jsonify({
                "clientSecret": intent.client_secret,
                "paymentIntentId": intent.id,
                "amount": intent.amount,
                "currency": intent.currency,
            })
        except stripe.error.StripeError:
            pass

    amount_cents = int(Decimal(str(order.total_amount)) * 100)
    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency="usd",
        metadata={"order_id": order.id, "user_id": user.id},
        idempotency_key=f"order_{order.id}",
    )
    order.stripe_payment_intent_id = intent.id
    db.session.commit()
    logger.info("PaymentIntent created %s for order %s", intent.id, order.id)
    return jsonify({
        "clientSecret": intent.client_secret,
        "paymentIntentId": intent.id,
        "amount": intent.amount,
        "currency": intent.currency,
    })


@app.route("/api/v1/payments/webhook", methods=["POST"])
def payments_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    webhook_secret = app.config["STRIPE_WEBHOOK_SECRET"]

    stripe = _get_stripe()

    if stripe and webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except stripe.error.SignatureVerificationError:
            logger.warning("Stripe webhook signature verification failed")
            return jsonify({"error": "Invalid signature"}), 400
    else:
        # Dev mode: parse raw JSON
        import json
        try:
            event = json.loads(payload)
        except Exception:
            return jsonify({"error": "Invalid JSON"}), 400

    event_type = event.get("type") if isinstance(event, dict) else event["type"]

    if event_type == "payment_intent.succeeded":
        data_obj = event["data"]["object"] if isinstance(event, dict) else event.data.object
        pi_id = data_obj.get("id