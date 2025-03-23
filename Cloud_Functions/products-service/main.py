import os
# import json
from flask import Flask, request, jsonify
from google.cloud import firestore
from flask_cors import CORS


# Set Firestore emulator environment
# os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8560"

# Initialize Firestore client
db = firestore.Client()
app = Flask(__name__)
CORS(app)


# Define your routes
@app.route('/add-product', methods=['POST'])
def add_product():
    data = request.json
    if not data or "ProductID" not in data:
        return jsonify({"error": "ProductID is required"}), 400
    product_id = data["ProductID"]
    db.collection("products").document(product_id).set(data)
    return jsonify({"message": f"Product {product_id} added successfully!"}), 201

@app.route('/getProductsforIndex', methods=['GET'])
def get_products():
    product_id = request.args.get('ProductID')
    category = request.args.get('Category')  # Handle category filtering for category.html

    products_ref = db.collection("products")
    
    if product_id:
        # Query Firestore for a single product by ProductID
        doc = products_ref.document(product_id).get()
        if not doc.exists:
            return jsonify({"error": "Product not found"}), 404
        return jsonify(doc.to_dict()), 200

    if category:
        # Query Firestore for products in the given category
        query = products_ref.where("Category", "==", category).stream()
        products = [doc.to_dict() for doc in query]
        return jsonify(products), 200

    # Fetch all products if no query parameters are provided
    products = [doc.to_dict() for doc in products_ref.stream()]
    return jsonify(products), 200


# Update Product
@app.route('/updateProduct', methods=['PUT'])
def update_product():
    try:
        data = request.json
        product_id = data.get('product_id')
        if not product_id:
            return jsonify({'error': 'Product ID is required'}), 400
        
        doc_ref = db.collection('products').document(product_id)
        doc = doc_ref.get()
        if not doc.exists:
            return jsonify({'error': 'Product not found'}), 404
        
        doc_ref.update(data)
        return jsonify({'message': 'Product updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Delete Product
@app.route('/deleteProduct', methods=['DELETE'])
def delete_product():
    product_id = request.args.get('product_id')
    try:
        doc_ref = db.collection('products').document(product_id)
        doc = doc_ref.get()
        if not doc.exists:
            return jsonify({'error': 'Product not found'}), 404

        doc_ref.delete()
        return jsonify({'message': 'Product deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# if __name__ == "__main__":
    # app.run(host="0.0.0.0", port=8080, debug=True)

# Add other routes...
port = int(os.environ.get("PORT", 8080))
app.run(host="0.0.0.0", port=port)
