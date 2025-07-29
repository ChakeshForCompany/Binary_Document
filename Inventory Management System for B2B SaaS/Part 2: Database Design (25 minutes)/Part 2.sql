/**1. Design Schema
I'll express the schema as SQL DDL statements and describe relationships.

Core Tables*/
Companies

sql
CREATE TABLE companies (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    -- Other fields (address, contact info) as needed
    UNIQUE(name)
);

Warehouses

sql
CREATE TABLE warehouses (
    id           SERIAL PRIMARY KEY,
    company_id   INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name         VARCHAR(255) NOT NULL,
    location     VARCHAR(255),
    UNIQUE(company_id, name)
    -- Index for fast lookups by company or name
);


Suppliers

sql
CREATE TABLE suppliers (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    contact_info VARCHAR(255),
    UNIQUE(name)
);


Products

sql
CREATE TABLE products (
    id           SERIAL PRIMARY KEY,
    sku          VARCHAR(64) NOT NULL UNIQUE,
    name         VARCHAR(255) NOT NULL,
    price        DECIMAL(12,2) NOT NULL,
    supplier_id  INTEGER REFERENCES suppliers(id),
    is_bundle    BOOLEAN DEFAULT FALSE
    -- Other optional product fields
);

ProductBundles
(To represent which products are included in a bundle)

sql
CREATE TABLE product_bundles (
    bundle_id    INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    product_id   INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity     INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY(bundle_id, product_id)
    -- bundle_id must refer to a product where is_bundle = TRUE
);

Inventory

sql
CREATE TABLE inventory (
    id           SERIAL PRIMARY KEY,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    product_id   INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity     INTEGER NOT NULL DEFAULT 0,
    UNIQUE(warehouse_id, product_id)
    -- Index for quick lookup by warehouse or product
);

InventoryChanges

sql
CREATE TABLE inventory_changes (
    id              SERIAL PRIMARY KEY,
    inventory_id    INTEGER NOT NULL REFERENCES inventory(id) ON DELETE CASCADE,
    change_type     VARCHAR(32) NOT NULL, -- e.g. 'received', 'sold', 'adjustment', etc.
    quantity_delta  INTEGER NOT NULL,
    occurred_at     TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    reference       VARCHAR(255) -- (optional: for order id, PO number, etc.)
    -- Index on (inventory_id, occurred_at) for efficient history queries
);

/**2. Identify Gaps & Questions for Product Team
Customer vs Internal Use:

Are products ever moved between companies, or is everything company-scoped?

Ownership & Access:

Can suppliers have access, or are they only references?

Warehouse Details:

Are locations or types ("retail", "distribution") for warehouses needed?

Inventory Units:

Is there tracking of units (e.g., "cases" vs "pieces")?

Bundles:

Can bundles include other bundles (nested)?

Can bundle composition change over time?

Product Variants:

Are product variants (color, size) in scope, or is every SKU unique?

Supplier Relationship:

Can a product have multiple suppliers? Is there a lead/preferred supplier?

Inventory Change Reasons:

Should change_type be an enum, and what values do you need?

Track “before”/“after” quantity or just delta?

Soft Deletes:

Should deleted items remain for history/audit?

Multi-Currency Pricing:

Will prices ever be in multiple currencies?

Timestamps/Auditing:

Do you require created_at/updated_at fields for all tables?

3. Explain Decisions
Surrogate Keys (id as SERIAL/PK):
For consistency and join efficiency.

Unique Constraints:
Enforce SKU uniqueness, warehouse uniqueness under a company, etc.

Referential Integrity:
Foreign keys with ON DELETE CASCADE to clean up dependent records.

Bundle Support:
Modelled with a self-referencing many-to-many table (product_bundles) to allow flexible bundle contents.

Inventory Model:
Inventory quantity is stored per product per warehouse; changes are logged in inventory_changes.

Indexes:
Indexes support lookup by warehouse/product and time (for historical queries).

Decimal for Price:
Precision is crucial, avoids currency roundoff errors.

Supplier-Product Relationship:
One-to-many for simplicity but flagged for clarification in open questions.

Expandable Inventory History:
Ability to extend inventory_changes to include reference fields or new change types.

Diagram (Textual ERD)
companies --< warehouses

suppliers --< products */

companies --< products (if needed, else products are global)

products --< inventory >-- warehouses

inventory --< inventory_changes

products --< product_bundles >-- products (for "bundle" relationships) '''
