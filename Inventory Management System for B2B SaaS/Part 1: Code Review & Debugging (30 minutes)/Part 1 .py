"""
1. Identify Issues
Technical Issues:
Atomicity: If inventory creation fails, product is still committed.
SKU Uniqueness: No check to ensure SKU is unique before creation.
Error Handling: No try/except or input validation; uncaught errors will crash or return 500s without helpful messages.
Data Validation: No checking of types or required/optional fields—e.g. price, warehouse_id, and initial_quantity might be missing or wrong type.
Price as Decimal: JSON and some DBs may interpret decimals as float, risking precision issues.
Multiple Warehouses Design: Your design assumes a product only gets added to a single warehouse, even though products can exist in many.
Committing Twice: Two db.session.commit() calls; if the second fails, you have a DB inconsistency.

Business Logic Issues:
SKU Uniqueness Violation: Duplicate SKUs might be inserted, breaking business rules.
Incorrect Initial State: No way to add the same product to multiple warehouses at once.
Poor Extensibility: Hardcoding initial_quantity, but what if you want to create with multiple warehouses/quantities?

2. Explain Impact
Issue	Impact
Atomicity	Partial DB updates (product without inventory), inconsistent DB state.
No SKU Uniqueness Check	Duplicate SKUs, corrupting inventory, search, and reporting.
No Error Handling	API returns generic 500s, poor client experience, harder debugging.
No Data Validation	Wrong data types, missing required data, or DB errors.
Decimal Price Handling	Float conversion might break currency accuracy.
Not Supporting Multi-Warehouse	Can't add initial stock for all warehouses the product should exist in.
Multiple Commits	Can leave data half-written if inventory fails.

"""

from flask import request, jsonify
from sqlalchemy.exc import IntegrityError
from decimal import Decimal, InvalidOperation

@app.route('/api/products', methods=['POST'])
def create_product():
    data = request.json or {}
    required_fields = ['name', 'sku', 'price', 'warehouse_quantities']
    
    # 1. Validate input
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Validate price is decimal-like
    try:
        price = Decimal(str(data['price']))
    except (InvalidOperation, TypeError, ValueError):
        return jsonify({"error": "Invalid price format."}), 400

    # 2. Ensure SKU uniqueness
    existing = Product.query.filter_by(sku=data['sku']).first()
    if existing:
        return jsonify({"error": "SKU must be unique."}), 409

    # 3. Validate warehouse quantities format and data
    # Expects e.g. 'warehouse_quantities': [{"warehouse_id": 1, "quantity": 50}, ...]
    warehouse_quantities = data['warehouse_quantities']
    if not isinstance(warehouse_quantities, list) or not warehouse_quantities:
        return jsonify({"error": "warehouse_quantities must be a non-empty list."}), 400
    for w in warehouse_quantities:
        if not isinstance(w, dict) or \
           'warehouse_id' not in w or 'quantity' not in w or \
           not isinstance(w['quantity'], int) or w['quantity'] < 0:
            return jsonify({"error": "Each warehouse entry must have warehouse_id and non-negative integer quantity."}), 400
      
    # 4. Atomic DB operation using a single transaction
    try:
        product = Product(
            name=data['name'],
            sku=data['sku'],
            price=price,
            # Include other optional fields here as needed
        )
        db.session.add(product)
        db.session.flush() # Get product id before committing

        # Insert into each warehouse inventory
        inventory_entries = []
        for wq in warehouse_quantities:
            inventory_entries.append(
                Inventory(
                    product_id=product.id,
                    warehouse_id=wq['warehouse_id'],
                    quantity=wq['quantity']
                )
            )
        
        db.session.add_all(inventory_entries)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "Database error, possibly invalid warehouse_id or duplicate entry."}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
    return jsonify({"message": "Product created", "product_id": product.id}), 201

'''
Key Changes Explained:
Input Validation: Check required fields, price format, and warehouse quantities.

SKU Uniqueness: Check for existing SKU before inserting.

Transaction safety: Only one commit; rollback on all errors.

Multi-warehouse Support: Allow creating inventory in multiple warehouses at once.

Decimal for Price: Use Decimal for money values.

Error Feedback: Returns helpful HTTP status codes and messages.

Extensibility: Optional fields can be easily added.

Ask the following if you need more context:

Exact Product/Inventory schema (especially types)

How initial quantity should be set if not provided

Behavior if inventory for a warehouse/product combo already exist
                              '''
