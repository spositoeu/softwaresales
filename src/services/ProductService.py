from psycopg2 import connect
import json

def get_products():
    """
    Fetches products from the PostgreSQL database and returns them as a JSON string.
    """
    try:
        conn = connect(dbname='softwaresales', user='postgres', password='', host='localhost', port='5432')
        cur = conn.cursor()

        cur.execute("SELECT id, name, description, price, category FROM products;")
        products = []
        for row in cur.fetchall():
            product = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'price': row[3],
                'category': row[4]
            }
            products.append(product)

        conn.close()

        return json.dumps(products, indent=4, default=str)

    except Exception as e:
        print(f"Error fetching products: {e}")
        return json.dumps({'error': str(e)})