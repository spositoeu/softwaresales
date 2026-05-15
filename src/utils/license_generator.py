import uuid
from datetime import date, timedelta
from typing import Literal

from src.database import Database

class LicenseGenerator:
    def __init__(self, db: Database):
        self.db = db

    def generate_license_key(self, product_id: str, license_type: Literal["perpetual", "subscription", "trial"]) -> str:
        """
        Generates a unique license key and saves it to the database.

        Args:
            product_id: The ID of the product the license is for.
            license_type: The type of license ("perpetual", "subscription", or "trial").

        Returns:
            The generated license key.
        """
        key = str(uuid.uuid4())

        if license_type == "subscription":
            expiry_date = date.today() + timedelta(days=365)
        elif license_type == "trial":
            expiry_date = date.today() + timedelta(days=7)
        else:
            expiry_date = date.today() + timedelta(days=1000)  # Perpetual licenses have no expiry

        license_data = {
            "product_id": product_id,
            "license_key": key,
            "license_type": license_type,
            "expiry_date": expiry_date,
            "created_at": date.today(),
        }

        self.db.add_license(license_data)
        return key

if __name__ == '__main__':
    # Example Usage (for testing purposes - this block will not be part of the final product)
    # Replace with your actual database initialization
    db = Database() # Assume Database class is defined elsewhere
    generator = LicenseGenerator(db)
    product_id = "product123"
    license_key = generator.generate_license_key(product_id, "subscription")
    print(f"Generated license key: {license_key}")
    db.close() # close the database connection