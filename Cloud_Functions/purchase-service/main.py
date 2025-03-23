from flask import Flask, request, jsonify
from datetime import datetime
import re
from flask_cors import CORS
import os
from google.cloud import firestore, pubsub_v1
from datetime import datetime
import uuid
import json


# Initialize Firestore client and Pub/Sub publisher
db = firestore.Client()
publisher = pubsub_v1.PublisherClient()

# Project and Topics
project_id = "buffs-e-commerce-platform"
payment_success_topic = "Payment-Success"
order_placed_topic = "Order-Placed"
payment_failure_topic = "Payment-Failure"

app = Flask(__name__)
CORS(app)

def publish_event(topic_name, message_data):
    """Publish a message to the specified Pub/Sub topic."""
    topic_path = publisher.topic_path(project_id, topic_name)
    message_bytes = json.dumps(message_data).encode("utf-8")
    publisher.publish(topic_path, data=message_bytes)
    print(f"Message published for: {topic_name}")

@app.route('/process-payment', methods=['POST'])
def process_payment():
    """Endpoint to process the payment."""
    try:
        # Get payment details from the request
        data = request.json
        
        user_id = data.get("userId")
        print("Received user_id:", user_id)  # Debugging log
        
        cardholder_name = data.get("cardholderName", "").strip()
        card_number = data.get("cardNumber", "").strip()
        expiry_date = data.get("expiryDate", "").strip()
        cvv = data.get("cvv", "").strip()
        total_price = data.get("totalAmount", "0.00").strip()

        # Validate payment details
        if not cardholder_name:
            return jsonify({"error": "Cardholder name is required"}), 400

        if not re.match(r"^\d{16}$", card_number):
            return jsonify({"error": "Invalid card number"}), 400

        try:
            expiry_date_obj = datetime.strptime(expiry_date, "%Y-%m-%d")
            if expiry_date_obj < datetime.now():
                return jsonify({"error": "Card has expired"}), 400
        except ValueError:
            return jsonify({"error": "Invalid expiry date format"}), 400

        if not re.match(r"^\d{3}$", cvv):
            return jsonify({"error": "Invalid CVV"}), 400

        if float(total_price) <= 0:
            return jsonify({"error": "Invalid total amount"}), 400

        # Simulate payment processing (replace with real payment gateway integration)
        if card_number.startswith("4") or card_number.startswith("5"):  # Example logic for testing (Visa cards start with 4)
            payment_status = "success"
        else:
            payment_status = "failure"

        # Return success or failure response
        if payment_status == "success":
            print("Payment marked as success")
            # return jsonify({"message": "Payment processed successfully"}), 200
            
            # Fetch cart details for the user
            cart_ref = db.collection('carts').document(user_id)
            cart_snapshot = cart_ref.get()
            cart_data = cart_snapshot.to_dict()

            # Debugging: Confirm cart data retrieval
            

            # return jsonify({"success": "Cart data retrieved successfully", "cart_data": cart_data}), 200

            if not cart_data or not cart_data.get("Items"):
                return jsonify({"error": "Cart is empty or not found"}), 400
            
            else:
                print("Cart data retrieved successfully:", cart_data)

            # Fetch billing address from the user collection
            user_ref = db.collection('users').document(user_id)
            user_snapshot = user_ref.get()
            user_data = user_snapshot.to_dict()

            if not user_data or not user_data.get("address"):
                return jsonify({"error": "Billing address not found for the user"}), 400

            billing_address = user_data["address"]  # Extract the billing address

            # Generate a unique purchase ID
            purchase_id = str(uuid.uuid4())

            # Publish payment success event
            publish_event(payment_success_topic, {
                
                "event_type": "payment_success",
                "purchase_id": purchase_id,
                "user_id": user_id,
                "total_price": float(total_price),
                "items": cart_data["Items"],
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            
            order_id = str(uuid.uuid4())

            # Publish order placed event
            publish_event(order_placed_topic, {
                "order_id":order_id,
                "event_type": "order_placed",
                "purchase_id": purchase_id,
                "user_id": user_id,
                "total_price": float(total_price),
                "items": cart_data["Items"],
                "billing_address": billing_address,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })

            # Save the purchase record to Firestore
            db.collection('purchases').document(purchase_id).set({
                "PurchaseID": purchase_id,
                "UserID": user_id,
                "TotalPrice": float(total_price),
                "Items": cart_data["Items"],
                "BillingAddress": billing_address,
                "Status": "Completed",
                "CreatedAt": datetime.now(),
                "UpdatedAt": datetime.now(),
            })

            # Clear the user's cart
            cart_ref.delete()  # Deletes the entire cart document

            return jsonify({"message": "Payment processed successfully"}), 200
        
        else:
            publish_event(payment_failure_topic, {
                    "event_type": "payment_failure",
                    "user_id": user_id,
                    "purchase_id": purchase_id,
                    "total_price": float(total_price),
                    "items": cart_data["Items"],
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
            return jsonify({"error": "Payment failed. Please check your details and try again"}), 400

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


port = int(os.environ.get("PORT", 8080))
app.run(host="0.0.0.0", port=port)
