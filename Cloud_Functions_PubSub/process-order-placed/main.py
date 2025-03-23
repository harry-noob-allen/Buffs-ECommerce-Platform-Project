from google.cloud import firestore, pubsub_v1, bigquery
import json
import base64
import logging
from datetime import datetime

# Initialize clients
db = firestore.Client()
publisher = pubsub_v1.PublisherClient()
bigquery_client = bigquery.Client()

# Configuration
project_id = "buffs-e-commerce-platform"
notification_topic_id = "Payment-Notification"
bigquery_table_id = "buffs-e-commerce-platform.buffs_commerce_analytics.orders_and_revenue"

# Configure logging
logging.basicConfig(level=logging.INFO)

def save_order_details(order_data):
    """Save the order details in Firestore and BigQuery."""
    try:
        # Firestore: Save order details
        order_ref = db.collection("orders").document(order_data["order_id"])
        order_data["Status"] = "Placed"
        order_data["CreatedAt"] = datetime.utcnow()
        order_data["UpdatedAt"] = datetime.utcnow()
        order_ref.set(order_data)
        logging.info(f"Order {order_data['order_id']} saved successfully in Firestore.")

        # BigQuery: Save order details
        row = {
                "order_id": str(order_data["order_id"]),  # Ensure STRING type
                "user_id": str(order_data["user_id"]),  # Ensure STRING type
                "order_total": float(order_data["total_price"]),  # Ensure FLOAT type
                "items": [  # Explicitly define an array of records (STRUCT)
                    {
                        "ProductID": str(item["ProductID"]),  # Ensure STRING type
                        "Price": float(item["Price"]),  # Ensure FLOAT type
                        "Quantity": int(item["Quantity"]),  # Ensure INTEGER type
                        "Name": str(item["Name"]),  # Ensure STRING type
                    }
                    for item in order_data["items"]
                ],
                "timestamp": order_data["timestamp"]  # Ensure TIMESTAMP format
        }
        errors = bigquery_client.insert_rows_json(bigquery_table_id, [row])
        if errors:
            for error in errors:
                logging.error(f"BigQuery insert error for order {order_data['order_id']}: {error}")
        else:
            logging.info(f"Order {order_data['order_id']} saved successfully in BigQuery.")
    except Exception as e:
        logging.error(f"Error saving order {order_data['order_id']}: {e}")

def publish_notification_event(message_data):
    """Publish a notification event to the Payment-Notification Pub/Sub topic."""
    topic_path = publisher.topic_path(project_id, notification_topic_id)
    try:
        message_bytes = json.dumps(message_data).encode("utf-8")
        future = publisher.publish(topic_path, data=message_bytes)
        logging.info(f"Published notification event with message ID: {future.result()}")
    except Exception as e:
        logging.error(f"Error publishing notification event: {e}")

def process_order_placed(event, context):
    """
    Cloud Function to process order-placed Pub/Sub messages.
    Triggered when a message is published to the order-placed topic.
    """
    try:
        # Decode the Pub/Sub message
        message_data = json.loads(base64.b64decode(event["data"]).decode("utf-8"))
        logging.info(f"Processing order-placed message: {message_data}")

        # Validate required fields
        required_fields = ["event_type", "order_id", "user_id", "items", "total_price", "timestamp"]
        for field in required_fields:
            if field not in message_data:
                logging.error(f"Missing field {field} in message. Skipping processing.")
                return

        # Validate the event type
        if message_data["event_type"] == "order_placed":
            # Save order details
            save_order_details({
                "order_id": message_data["order_id"],
                "user_id": message_data["user_id"],
                "items": message_data["items"],
                "total_price": message_data["total_price"],
                "timestamp": message_data["timestamp"]
            })

            # Publish a notification event
            publish_notification_event({
                "event_type": "order_placed_notification",
                "user_id": message_data["user_id"],
                "order_id": message_data["order_id"],
                "timestamp": message_data["timestamp"]
            })
        else:
            logging.warning("Event type mismatch. Skipping message.")
    except Exception as e:
        logging.error(f"Error processing message: {e}")
