from google.cloud import firestore, pubsub_v1
import json
import base64
import logging
import time

# Initialize Firestore and Pub/Sub clients
db = firestore.Client()
publisher = pubsub_v1.PublisherClient()

# Configuration
project_id = "buffs-e-commerce-platform"
notification_topic_id = "Payment-Notification"

# Configure logging
logging.basicConfig(level=logging.INFO)

def restore_reserved_stock(items):
    """Restore reserved stock for items in the cart after payment failure."""
    def restore_stock_transaction(transaction, product_ref, quantity):
        product = transaction.get(product_ref).to_dict()
        reserved_stock = product.get("ReservedStock", 0)
        if reserved_stock >= quantity:
            transaction.update(product_ref, {"ReservedStock": reserved_stock - quantity})
            logging.info(f"Restored {quantity} units to reserved stock for ProductID {product_ref.id}.")
        else:
            raise ValueError(f"Not enough reserved stock to restore for ProductID {product_ref.id}. Reserved: {reserved_stock}")

    for item in items:
        product_id = item["ProductID"]
        quantity = item["Quantity"]
        product_ref = db.collection("products").document(product_id)

        try:
            db.run_transaction(lambda transaction: restore_stock_transaction(transaction, product_ref, quantity))
        except ValueError as e:
            logging.warning(f"Stock adjustment failed for ProductID {product_id}: {e}")
        except Exception as e:
            logging.error(f"Error restoring reserved stock for ProductID {product_id}: {e}")

def publish_notification_event(message_data):
    """Publish a notification event to the payment-notifications topic."""
    topic_path = publisher.topic_path(project_id, notification_topic_id)
    max_retries = 3

    for attempt in range(max_retries):
        try:
            message_bytes = json.dumps(message_data).encode("utf-8")
            future = publisher.publish(topic_path, data=message_bytes)
            logging.info(f"Published notification event with message ID: {future.result()}")
            break
        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logging.error(f"Error publishing notification event after {max_retries} attempts: {e}")

def process_payment_failure(event, context):
    """
    Cloud Function to process payment-failure Pub/Sub messages.
    Triggered when a message is published to the payment-failure topic.
    """
    try:
        # Decode the Pub/Sub message
        message_data = json.loads(base64.b64decode(event["data"]).decode("utf-8"))
        logging.info(f"Processing payment-failure message: {message_data}")

        # Validate required fields
        required_fields = ["event_type", "user_id", "purchase_id", "items", "timestamp"]
        for field in required_fields:
            if field not in message_data:
                logging.error(f"Missing field {field} in message. Skipping processing.")
                return

        # Validate the event type
        if message_data["event_type"] == "payment_failure":
            # Restore reserved stock
            restore_reserved_stock(message_data["items"])

            # Publish a notification event
            publish_notification_event({
                "event_type": "payment_failure_notification",
                "user_id": message_data["user_id"],
                "purchase_id": message_data["purchase_id"],
                "reason": "Payment failed",
                "timestamp": message_data["timestamp"]
            })
        else:
            logging.warning("Event type mismatch. Skipping message.")

    except Exception as e:
        logging.error(f"Error processing message: {e}")
