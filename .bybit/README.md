# Bybit OpenAPI RSA Integration

## Setup Steps

1. **Upload public key to Bybit**
   - Log in to Bybit → Account → API Management
   - Create a new API key, choose **RSA** signature type
   - Paste the contents of `public_key.pem` into the "Public Key" field
   - Enable only the permissions you need (never enable Withdraw for AI keys)
   - Recommended: use a sub-account with a 5,000 USD balance cap

2. **Store credentials as environment variables**
   ```bash
   export BYBIT_API_KEY="your-api-key-from-bybit"
   export BYBIT_API_PRIVATE_KEY_PATH="/path/to/private_key.pem"
   ```

3. **Keep the private key secure**
   - Never commit `private_key.pem` to any repository
   - Store it outside the project directory or in a secrets manager
   - The private key file is listed in `.gitignore`

## Authentication

This integration uses **RSA-SHA256** signing (Bybit v5 API).

Signature flow:
```
timestamp + api_key + recv_window + query_string_or_body
→ sign with RSA private key (PKCS#1 v1.5, SHA-256)
→ base64-encode → send as `sign` header
```

## Rate Limits

- GET requests: minimum 100 ms between calls
- POST requests: minimum 300 ms between calls
- Use batch endpoints for bulk operations
