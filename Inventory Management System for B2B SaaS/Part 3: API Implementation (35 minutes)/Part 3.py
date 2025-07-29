'''
Using Python with Flask and SQLAlchemy.
"Low stock" means inventory quantity < product’s threshold.
“Recent sales activity” means at least one 'sale' transaction in that warehouse for the product in the past 30 days.
Must include supplier info for each alert.
Estimate days_until_stockout as:
(current_stock) / (avg daily sales in last 30 days), rounded up.
'''

from flask import Flask, jsonify, request
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
import math

app = Flask(__name__)

# Assume: SQLAlchemy models are defined as per schema above
# Models: Company, Warehouse, Product, Inventory, InventoryChange, Supplier

@app.route('/api/companies/<int:company_id>/alerts/low-stock')
def low_stock_alerts(company_id):
    # --- CONFIGURATION ---
    RECENT_SALES_DAYS = 30

    # 1. Find all company warehouses
    warehouses = Warehouse.query.filter_by(company_id=company_id).all()
    warehouse_ids = [w.id for w in warehouses]

    # 2. Find inventory records below threshold and with recent sales
    # First: build a subquery for average daily sales in last N days
    since = datetime.utcnow() - timedelta(days=RECENT_SALES_DAYS)
    sales_subq = (
        db.session.query(
            Inventory.inventory_id.label('inventory_id'),
            func.sum(InventoryChange.quantity_delta * -1).label('total_sales'),  # quantity_delta: -5 for sale of 5
            (func.sum(InventoryChange.quantity_delta * -1) / RECENT_SALES_DAYS).label('avg_daily_sales')
        )
        .filter(
            InventoryChange.change_type == 'sale',
            InventoryChange.occurred_at >= since
        )
        .join(Inventory, InventoryChange.inventory_id == Inventory.id)
        .filter(Inventory.warehouse_id.in_(warehouse_ids))
        .group_by(Inventory.inventory_id)
        .subquery()
    )

    # 3. Join inventory, products, thresholds, supplier
    results = (
        db.session.query(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.sku,
            Inventory.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            Inventory.quantity.label("current_stock"),
            Product.low_stock_thresh.label("threshold"),
            Supplier.id.label("supplier_id"),
            Supplier.name.label("supplier_name"),
            Supplier.contact_email,
            sales_subq.c.avg_daily_sales
        )
        .join(Inventory, Inventory.product_id == Product.id)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .outerjoin(sales_subq, Inventory.id == sales_subq.c.inventory_id)
        .join(Supplier, Product.supplier_id == Supplier.id)
        .filter(
            Inventory.warehouse_id.in_(warehouse_ids),
            Inventory.quantity < Product.low_stock_thresh,
            sales_subq.c.total_sales != None,              # Only products with recent sales
            sales_subq.c.total_sales > 0
        )
        .all()
    )

    # 4. Build alerts JSON
    alerts = []
    for row in results:
        avg_daily_sales = row.avg_daily_sales
        cur_stock = row.current_stock if row.current_stock is not None else 0
        threshold = row.threshold if row.threshold is not None else 1  # fallback
        # Estimate days until stockout
        if avg_daily_sales and avg_daily_sales > 0:
            days_until_stockout = math.ceil(cur_stock / avg_daily_sales)
        else:
            days_until_stockout = None  # can't estimate

        alert = {
            "product_id": row.product_id,
            "product_name": row.product_name,
            "sku": row.sku,
            "warehouse_id": row.warehouse_id,
            "warehouse_name": row.warehouse_name,
            "current_stock": cur_stock,
            "threshold": threshold,
            "days_until_stockout": days_until_stockout,
            "supplier": {
                "id": row.supplier_id,
                "name": row.supplier_name,
                "contact_email": row.contact_email
            }
        }
        alerts.append(alert)

    return jsonify({
        "alerts": alerts,
        "total_alerts": len(alerts)
    }), 200

# --- ENDPOINT END ---

'''Edge Case Handling & Comments
No Recent Sales: Products/warehouses without sales in period are ignored (sales_subq.c.total_sales != None).

Zero or Null Threshold: Fallback/defaults are used—ideally, your schema enforces presence.

Division by Zero: Checked—days_until_stockout is None if avg_daily_sales is 0.

Suppliers: Assumes one supplier/product; if many, code must aggregate or choose preferred.

Multiple Warehouses: Can alert for same product in multiple warehouses.

Design Justifications
Indexes:

Indexes should exist on (warehouse_id, product_id) on inventory and inventory_changes tables for join performance.

Foreign keys ensure data integrity.

Unique constraints prevent duplication (SKU, bundle contents).'''

