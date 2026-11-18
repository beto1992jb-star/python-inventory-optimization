"""
Orders & inventory report.

Reads orders.csv and inventory.csv and prints:
  - number of unique orders
  - revenue from shipped orders
  - late deliveries (count and percentage)
  - orders whose SKU is not in the inventory
  - top 5 customers by revenue
  - SKUs that need to be reordered
"""
import pandas as pd

ORDERS_FILE = "orders.csv"
INVENTORY_FILE = "inventory.csv"


def load_orders(path):
    """Load the orders file and parse the date columns."""
    df = pd.read_csv(path)
    # FIXED: Removed duplicate order records that inflated revenue, late deliveries, and unknown SKU counts
    df = df.drop_duplicates()
    # FIXED: Corrected date format from %Y-%d-%m to %Y-%m-%d
    df["order_date"] = pd.to_datetime(df["order_date"], format="%Y-%m-%d")
    df["promised_date"] = pd.to_datetime(df["promised_date"])
    df["delivered_date"] = pd.to_datetime(df["delivered_date"])
    return df


def add_line_totals(df):
    """Add a line_total column (qty x unit_price) to every order."""
    # FIXED: Vectorized multiplication to eliminate slow iterrows() bottleneck (< 1s execution)
    df["line_total"] = df["qty"] * df["unit_price"]
    return df


def enrich_with_inventory(orders, inventory):
    """Attach product info to each order. Keep orders even if the SKU is unknown."""
    # FIXED: Changed inner join to left join to preserve orders with unknown SKUs
    return pd.merge(orders, inventory, on="sku", how="left")


def late_deliveries(shipped):
    """Shipped orders delivered after the promised date."""
    return shipped[shipped["delivered_date"] > shipped["promised_date"]]


def top_customers(shipped, n=5):
    """The n customers with the highest revenue."""
    return shipped.groupby("customer")["line_total"].sum().nlargest(n)


def skus_to_reorder(inventory):
    """SKUs whose stock is at or below the reorder point."""
    # FIXED: Changed < to <= to include items whose stock equals their reorder point
    return inventory[inventory["stock"] <= inventory["reorder_point"]].sort_values("sku")


def main():
    orders = load_orders(ORDERS_FILE)
    inventory = pd.read_csv(INVENTORY_FILE)

    orders = add_line_totals(orders)
    data = enrich_with_inventory(orders, inventory)

    # FIXED: Added parentheses to fix operator precedence in boolean filtering
    shipped = data[(data["qty"] > 0) & (data["status"] == "shipped")]
    late = late_deliveries(shipped)

    print("=== ORDERS & INVENTORY REPORT ===")
    print(f"Unique orders: {len(data)}")
    print(f"Shipped revenue: {shipped['line_total'].sum():,.2f}")
    print(f"Late deliveries: {len(late)} ({len(late) / len(shipped) * 100:.1f}%)")
    print(f"Orders with unknown SKU: {data['product'].isna().sum()}")

    print("\nTop 5 customers by revenue:")
    for customer, value in top_customers(shipped).items():
        print(f"  {customer}: {value:,.2f}")

    print("\nSKUs to reorder:")
    for _, row in skus_to_reorder(inventory).iterrows():
        print(f"  {row['sku']}: stock {row['stock']} (reorder point {row['reorder_point']})")


if __name__ == "__main__":
    main()