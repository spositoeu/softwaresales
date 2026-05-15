import uuid
import boto3
import os
from cryptography.fernet import Fernet

# Configuration (Replace with your actual values)
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
ENCRYPTION_KEY_PATH = "encryption_key.key"  # Path to the Fernet key file

def generate_license_key():
    """Generates a random license key."""
    return str(uuid.uuid4())

def encrypt_key(key):
    """Encrypts the key using Fernet."""
    f = Fernet(key)
    return f.encrypt(key.encode())

def save_license_key_to_s3(license_key):
    """Saves the license key to S3 with a signed URL."""
    s3 = boto3.client('s3',
                       aws_access_key_id=AWS_ACCESS_KEY_ID,
                       aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

    key_name = f"license_keys/{license_key}.key"
    s3.put_object(Bucket=S3_BUCKET_NAME, Key=key_name, Body=license_key)
    
    # Generate a signed URL.  This is a placeholder, a real implementation would
    # use a service like AWS Lambda to generate and manage the signed URLs.
    signed_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{key_name}"
    return signed_url

def main():
    """Main function to generate and save the license key."""
    license_key = generate_license_key()
    encrypted_key = encrypt_key(license_key)

    # Save the encrypted key to a file for later use.  This is a simplified approach
    #  For production, store the key securely (e.g., AWS KMS, HashiCorp Vault)
    with open(ENCRYPTION_KEY_PATH, 'wb') as f:
        f.write(encrypted_key)

    signed_url = save_license_key_to_s3(license_key)
    print(f"Generated License Key: {license_key}")
    print(f"Signed URL: {signed_url}")

if __name__ == "__main__":
    main()