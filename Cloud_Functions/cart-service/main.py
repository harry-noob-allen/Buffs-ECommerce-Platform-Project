import os
from flask import Flask, request, jsonify
from google.cloud import firestore, pubsub_v1
from datetime import datetime
import json
import time
import logging
import google.cloud.logging
from flask_cors import CORS

# Initialize Firestore and Pub/Sub clients
db = firestore.Client()
publisher = pubsub_v1.PublisherClient()

# Configure logging
client = google.cloud.logging.Client()
client.setup_logging()

# Pub/Sub topic and project configuration
project_id = "buffs-e-commerce-platform"
topic_id = "Cart-Finalized"

# Flask app initialization
app = Flask(__name__)
CORS(app)

@app.route('/add-to-cart/<UserID>', methods=['POST'])
def add_to_cart(UserID):
    """Add an item to the cart for the specified UserID after validating stock."""
    try:
        # Parse the incoming item data from the request body
        item = request.json.get('Item')

        if not UserID or not item:
            return jsonify({'error': 'UserID and Item are required'}), 400

        # Extract product details from the item
        product_id = item.get('ProductID')
        quantity = item.get('Quantity')

        if not product_id or not quantity:
            return jsonify({'error': 'ProductID and Quantity are required'}), 400

        # Fetch product details from Firestore
        product_ref = db.collection('products').document(product_id)
        product = product_ref.get()

        if not product.exists:
            return jsonify({'error': f'Product {product_id} does not exist'}), 404

        product_data = product.to_dict()
        available_stock = product_data.get('Stock', 0) - product_data.get('ReservedStock', 0)

        if available_stock < quantity:
            return jsonify({
                'error': f'Insufficient stock for ProductID {product_id}.',
                'available_stock': available_stock,
                'requested_quantity': quantity
            }), 400

        # Fetch the user's existing cart from Firestore
        cart_ref = db.collection('carts').document(UserID)
        cart_snapshot = cart_ref.get()
        cart = cart_snapshot.to_dict() or {"UserID": UserID, "Items": []}

        # Check if the product already exists in the cart
        for cart_item in cart["Items"]:
            if cart_item["ProductID"] == product_id:
                cart_item["Quantity"] += quantity
                break
        else:
            # Add the new item to the cart if it doesn't already exist
            cart["Items"].append({
                "Name": product_data.get("Name"),
                "Price": product_data.get("Price"),
                "ProductID": product_id,
                "Quantity": quantity
            })

        # Update the cart in Firestore
        cart_ref.set(cart)

        # Update the ReservedStock for the product to ensure availability
        new_reserved_stock = product_data.get('ReservedStock', 0) + quantity
        product_ref.update({"ReservedStock": new_reserved_stock})

        logging.info(f"Added item {item} to cart for UserID {UserID}.")
        return jsonify({'message': 'Item added to cart successfully!'}), 201

    except Exception as e:
        logging.error(f"Error adding to cart for UserID {UserID}: {str(e)}")
        return jsonify({'error': str(e)}), 400
    
@app.route('/get-cart', methods=['GET'])
def get_cart():
    user_id = request.args.get('UserID')
    if not user_id:
        return jsonify({'error': 'UserID is required'}), 400

    cart_ref = db.collection('carts').document(user_id)
    cart = cart_ref.get().to_dict()
    if not cart:
        return jsonify({'message': 'Cart is empty'}), 404
    return jsonify(cart), 200

@app.route('/update-cart', methods=['PUT'])
def update_cart():
    data = request.json
    user_id = data.get('UserID')
    item_index = data.get('ItemIndex')
    new_quantity = data.get('Quantity')
    if not user_id or item_index is None or new_quantity is None:
        return jsonify({'error': 'UserID, ItemIndex, and Quantity are required'}), 400

    cart_ref = db.collection('carts').document(user_id)
    cart = cart_ref.get().to_dict()
    if not cart:
        return jsonify({'error': 'Cart not found'}), 404

    try:
        cart['Items'][item_index]['Quantity'] = new_quantity
        cart_ref.set(cart)
        return jsonify({'message': 'Cart updated successfully!'}), 200
    except IndexError:
        return jsonify({'error': 'Item index out of range'}), 400

@app.route('/remove-from-cart', methods=['DELETE'])
def remove_from_cart():
    data = request.json
    user_id = data.get('UserID')
    item_index = data.get('ItemIndex')
    if not user_id or item_index is None:
        return jsonify({'error': 'UserID and ItemIndex are required'}), 400

    cart_ref = db.collection('carts').document(user_id)
    cart = cart_ref.get().to_dict()
    if not cart:
        return jsonify({'error': 'Cart not found'}), 404

    try:
        del cart['Items'][item_index]
        cart_ref.set(cart)
        return jsonify({'message': 'Item removed from cart successfully!'}), 200
    except IndexError:
        return jsonify({'error': 'Item index out of range'}), 400



@app.route('/finalize-cart', methods=['POST'])
def finalize_cart():
    """Finalize the cart and publish the cart-finalized event."""
    try:
        data = request.json
        user_id = data.get('UserID')
        if not user_id:
            return jsonify({'error': 'UserID is required'}), 400

        # Retrieve the user's cart
        cart_ref = db.collection('carts').document(user_id)
        cart = cart_ref.get().to_dict()
        if not cart or not cart.get('Items'):
            return jsonify({'error': 'Cart is empty or not found'}), 400

        # Check if the cart is already finalized
        if cart.get('Finalized', False):
            return jsonify({'error': 'Cart has already been finalized.'}), 400

        # Mark the cart as finalized
        cart['Finalized'] = True
        cart_ref.set(cart)

        # Calculate total price
        original_price = round(sum(item['Quantity'] * item['Price'] for item in cart['Items']), 2)
        tax = round(original_price * 0.1, 2)  # 10% tax
        total_price = round(original_price + tax, 2)


        # Publish the cart-finalized event
        topic_path = publisher.topic_path(project_id, topic_id)
        message_data = {
            "event_type": "cart_finalized",
            "user_id": user_id,
            "items": cart['Items'],
            "total_price": total_price,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        message_bytes = json.dumps(message_data).encode("utf-8")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                future = publisher.publish(topic_path, data=message_bytes)
                message_id = future.result()
                logging.info(f"Published cart-finalized event with message ID: {message_id}")
                break
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise

        return jsonify({'message': 'Cart finalized successfully!', 'total_price': total_price}), 200

    except Exception as e:
        logging.error(f"Error finalizing cart: {str(e)}")
        return jsonify({'error': str(e)}), 500


port = int(os.environ.get("PORT", 8080))
app.run(host="0.0.0.0", port=port)