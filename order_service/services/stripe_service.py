import stripe
import logging
from softwaresales.models import Order, Product

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

logger = logging.getLogger(__name__)

class StripeService:
    def __init__(self):
        pass

    def create_payment_intent(self, amount, currency, product_id):
        try:
            product = Product.objects.get(id=product_id)
            data = {
                'currency': currency,
                'amount': amount,
                'product_ids': [product.id]
            }
            intent = stripe.PaymentIntent.create(**data)
            return intent.id
        except Product.DoesNotExist:
            logger.exception("Product not found for payment intent creation")
            raise

    def process_webhook(self, payload, sig_header):
        # Implement webhook logic here
        logger.info(f"Webhook payload: {payload}")
        # Example: Check for events like 'payment_intent.webhook'
        try:
            event = stripe.Event.construct_event(
                payload, sig_header)

            # Handle the event
            if event.type == 'payment_intent.webhook':
                logger.info(f"Payment Intent Webhook Event: {event}")
                # Your webhook logic here (e.g., update order status)
            else:
                logger.warning(f"Unhandled webhook event type: {event.type}")

        except stripe.error.WebhookError as e:
            logger.exception(f"Webhook Error: {e}")

    def capture_payment_intent(self, payment_intent_id):
        try:
            intent = stripe.PaymentIntent.capture(payment_intent_id)
            return intent.status
        except stripe.error.PaymentIntentError as e:
            logger.exception(f"Error capturing payment intent: {e}")
            raise