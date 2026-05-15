import uuid
import stripe
from softwaresales.utils import generate_license_key

def create_order(user_id, product_id, quantity):
    """
    Creates a new order, processes payment via Stripe, and generates a license key.
    """
    order_id = str(uuid.uuid4())
    order_data = {
        'order_id': order_id,
        'user_id': user_id,
        'product_id': product_id,
        'quantity': quantity,
        'status': 'pending',
        'created_at': datetime.datetime.now()
    }

    # Process Payment with Stripe
    try:
        stripe.PaymentIntent.create(
            amount=product_data[product_id]['price'] * quantity,
            currency='usd',
            automatic_payment_method=True,
        )
    except stripe.error.StripeError as e:
        print(f"Stripe payment error: {e}")
        return None

    # Generate License Key
    license_key = generate_license_key(user_id, product_id, quantity)
    order_data['license_key'] = license_key

    # Save Order to Database (implementation placeholder)
    # In a real implementation, save order_data to the database
    print(f"Order created: {order_data}")

    return order_data