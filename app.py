from flask import Flask, request, jsonify
import os
import hashlib
import hmac
import asyncio

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Bot is running! Restricted Content Download Bot by @idfinderpro'

@app.route('/health')
def health_check():
    return {'status': 'healthy', 'service': 'Restricted Content Download Bot'}, 200


# Crypto Pay webhook endpoint
@app.route('/webhook/cryptopay', methods=['POST'])
def crypto_pay_webhook():
    """
    Receive payment confirmations from Crypto Pay API.
    This webhook is triggered when a user completes a crypto payment.
    """
    try:
        from config import CRYPTO_PAY_API_TOKEN
        
        # Get the signature from headers
        signature = request.headers.get('crypto-pay-api-signature', '')
        
        # Get raw body for signature verification
        raw_body = request.get_data(as_text=True)
        
        # Verify signature
        if CRYPTO_PAY_API_TOKEN:
            secret = hashlib.sha256(CRYPTO_PAY_API_TOKEN.encode()).digest()
            expected_signature = hmac.new(secret, raw_body.encode(), hashlib.sha256).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                print(f"[WEBHOOK] Invalid signature! Expected: {expected_signature}, Got: {signature}")
                return jsonify({'error': 'Invalid signature'}), 401
        
        # Parse the webhook data
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data'}), 400
        
        update_type = data.get('update_type')
        payload = data.get('payload', {})
        
        print(f"[WEBHOOK] Received: {update_type}")
        
        if update_type == 'invoice_paid':
            # Invoice was paid - activate premium
            invoice_id = payload.get('invoice_id')
            invoice_payload = payload.get('payload', '')  # Contains "user_id:plan"
            paid_amount = payload.get('paid_amount') or payload.get('amount')
            paid_asset = payload.get('paid_asset', 'crypto')
            
            print(f"[WEBHOOK] Invoice {invoice_id} paid! Payload: {invoice_payload}")
            
            # Parse user_id and plan from payload
            if ':' in invoice_payload:
                user_id, plan = invoice_payload.split(':', 1)
                user_id = int(user_id)
                
                # Run async function to activate premium
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    loop.run_until_complete(activate_premium_from_webhook(
                        invoice_id, user_id, plan, paid_amount, paid_asset
                    ))
                finally:
                    loop.close()
                
                return jsonify({'ok': True, 'message': 'Premium activated'}), 200
            else:
                print(f"[WEBHOOK] Invalid payload format: {invoice_payload}")
                return jsonify({'error': 'Invalid payload'}), 400
        
        return jsonify({'ok': True}), 200
        
    except Exception as e:
        print(f"[WEBHOOK] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


async def activate_premium_from_webhook(invoice_id, user_id, plan, paid_amount, paid_asset):
    """Activate premium subscription from webhook callback"""
    import time
    from database.db import db
    
    # Plan durations
    plan_durations = {"1day": 1, "7day": 7, "30day": 30}
    days = plan_durations.get(plan, 1)
    
    # Calculate expiry
    duration = days * 24 * 60 * 60  # Convert to seconds
    
    # Check if user already has premium
    user = await db.col.find_one({'id': user_id})
    is_premium = await db.is_premium(user_id)
    
    if is_premium and user and user.get('premium_expiry'):
        current_expiry = user.get('premium_expiry')
        if current_expiry > time.time():
            expiry_time = current_expiry + duration
        else:
            expiry_time = time.time() + duration
    else:
        expiry_time = time.time() + duration
    
    # Set premium
    await db.set_premium(user_id, True, expiry_time)
    
    # Update invoice status
    await db.update_crypto_invoice_status(invoice_id, "paid", time.time())
    
    print(f"[WEBHOOK] Premium activated for user {user_id} - {days} days until {expiry_time}")


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
