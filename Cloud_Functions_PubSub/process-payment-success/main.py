from google.cloud import firestore
import json
import base64
import logging

# Initialize Firestore client
db = firestore.Client()

# Configure logging
logging.basicConfig(level=logging.INFO)

def deduct_reserved_stock_transaction(transaction, product_ref, quantity):
    product = transaction.get(product_ref).to_dict()
    reserved_stock = product.get("ReservedStock", 0)
    stock = product.get("Stock", 0)

    if reserved_stock >= quantity:
        transaction.update(product_ref, {
            "ReservedStock": reserved_stock - quantity,
            "Stock": stock - quantity,
        })
        logging.info(f"Deducted {quantity} from stock and reserved stock for ProductID {product_ref.id}.")
    else:
        raise ValueError(f"Not enough reserved stock for ProductID {product_ref.id}. Reserved: {reserved_stock}")


def deduct_reserved_stock(items):
    for item in items:
        product_id = item["ProductID"]
        quantity = item["Quantity"]
        product_ref = db.collection("products").document(product_id)

        try:
            db.run_transaction(lambda transaction: deduct_reserved_stock_transaction(transaction, product_ref, quantity))
        except ValueError as e:
            logging.warning(f"Stock adjustment failed for ProductID {product_id}: {e}")
        except Exception as e:
            logging.error(f"Error deducting stock for ProductID {product_id}: {e}")


def process_payment_success(event, context):
    """
    Cloud Function to process payment-success Pub/Sub messages.
    Triggered when a message is published to the payment-success topic.
    """
    try:
        # Decode the Pub/Sub message
        message_data = json.loads(base64.b64decode(event["data"]).decode("utf-8"))
        logging.info(f"Processing payment-success message: {message_data}")

        # Validate the event type
        if message_data.get("event_type") == "payment_success":
            deduct_reserved_stock(message_data["items"])
        else:
            logging.warning("Event type mismatch. Skipping message.")

    except Exception as e:
        logging.error(f"Error processing message: {e}")
