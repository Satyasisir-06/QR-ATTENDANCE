import secrets

# Generate a secure secret key for Flask
secret_key = secrets.token_hex(32)

print("=" * 60)
print("🔑 Generated Secret Key for Flask")
print("=" * 60)
print(f"\n{secret_key}\n")
print("Copy this value and set it as SECRET_KEY in Vercel")
print("Environment Variables: Settings → Environment Variables")
print("=" * 60)
