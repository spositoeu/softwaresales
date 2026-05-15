import stripe
import os

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

def create_payment_intent(amount, currency):
    """
    Creates a Stripe PaymentIntent.
    """
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            automatic_payment_methods={
                'enabled': True,
            }
        )
        return payment_intent.id
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        raise