from google.cloud import firestore
import json
import base64
import logging

# Initialize Firestore client
db = firestore.Client()

# Configure logging
logging.basicConfig(level=logging.INFO)

def reserve_inventory(items):
    """Reserve inventory for items in the cart."""
    for item in items:
        product_id = item["ProductID"]
        quantity = item["Quantity"]

        try:
            # Reference to the product in Firestore
            product_ref = db.collection("products").document(product_id)
            product = product_ref.get()

            if product.exists:
                product_data = product.to_dict()
                available_stock = product_data["Stock"] - product_data.get("ReservedStock", 0)

                if available_stock >= quantity:
                    # Increment ReservedStock
                    product_ref.update({"ReservedStock": firestore.Increment(quantity)})
                    logging.info(f"Reserved {quantity} units for ProductID {product_id}.")
                else:
                    logging.warning(f"Insufficient stock for ProductID {product_id}. Available: {available_stock}")
            else:
                logging.error(f"ProductID {product_id} does not exist.")
        except Exception as e:
            logging.error(f"Error reserving inventory for ProductID {product_id}: {e}")

def process_cart_finalized(event, context):
    """
    Cloud Function to process a cart-finalized Pub/Sub message.
    Triggered when a message is published to the cart-finalized topic.
    """
    try:
        # Decode the Pub/Sub message
        message_data = json.loads(base64.b64decode(event["data"]).decode("utf-8"))
        logging.info(f"Processing cart-finalized message: {message_data}")

        # Ensure the event type is "cart_finalized"
        if message_data.get("event_type") == "cart_finalized":
            reserve_inventory(message_data["items"])
        else:
            logging.warning("Event type mismatch. Skipping message.")

    except Exception as e:
        logging.error(f"Error processing message: {e}")
