"""
Crypto Pay Integration for Premium Subscriptions
Uses @CryptoBot / @send Crypto Pay API
"""
import time
import hashlib
import hmac
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import db
from config import ADMINS, CRYPTO_PAY_API_TOKEN, CRYPTO_PAY_TESTNET

# Crypto Pay API URLs
CRYPTO_PAY_API_URL = "https://testnet-pay.crypt.bot/api" if CRYPTO_PAY_TESTNET else "https://pay.crypt.bot/api"

# Supported cryptocurrencies (testnet has JET, mainnet doesn't)
if CRYPTO_PAY_TESTNET:
    SUPPORTED_ASSETS = ["USDT", "TON", "BTC", "ETH", "LTC", "BNB", "TRX", "USDC", "JET"]
else:
    SUPPORTED_ASSETS = ["USDT", "TON", "BTC", "ETH", "LTC", "BNB", "TRX", "USDC"]

# Plan durations in days
PLAN_DURATIONS = {
    "1day": 1,
    "7day": 7,
    "30day": 30
}


async def crypto_pay_request(method: str, params: dict = None):
    """Make a request to Crypto Pay API"""
    import aiohttp
    
    if not CRYPTO_PAY_API_TOKEN:
        return None, "Crypto Pay API token not configured"
    
    url = f"{CRYPTO_PAY_API_URL}/{method}"
    headers = {
        "Crypto-Pay-API-Token": CRYPTO_PAY_API_TOKEN,
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            if params:
                async with session.post(url, headers=headers, json=params) as response:
                    try:
                        data = await response.json()
                    except:
                        response_text = await response.text()
                        return None, f"Invalid JSON response: {response_text[:200]}"
            else:
                async with session.get(url, headers=headers) as response:
                    try:
                        data = await response.json()
                    except:
                        response_text = await response.text()
                        return None, f"Invalid JSON response: {response_text[:200]}"
            
            if data.get("ok"):
                return data.get("result"), None
            else:
                error_obj = data.get("error", {})
                if isinstance(error_obj, dict):
                    error_msg = error_obj.get("message") or error_obj.get("name") or str(error_obj)
                else:
                    error_msg = str(error_obj) if error_obj else "Unknown error"
                return None, error_msg
                
    except Exception as e:
        return None, str(e)


async def create_crypto_invoice(user_id: int, plan: str, amount_usd: float):
    """Create a crypto payment invoice"""
    
    # Get plan duration
    days = PLAN_DURATIONS.get(plan, 1)
    
    # Use crypto currency type with USDT as base (more reliable)
    params = {
        "currency_type": "crypto",
        "asset": "USDT",
        "amount": str(amount_usd),
        "description": f"Premium {days} Day(s) - ID Finder Pro Bot",
        "hidden_message": "Thank you for your purchase! Your premium has been activated.",
        "paid_btn_name": "openBot",
        "paid_btn_url": "https://t.me/idfinderpro_bot",
        "payload": f"{user_id}:{plan}",
        "allow_comments": False,
        "allow_anonymous": True,
        "expires_in": 3600
    }
    
    result, error = await crypto_pay_request("createInvoice", params)
    
    if error:
        return None, error
    
    return result, None



async def check_invoice_status(invoice_id: int):
    """Check the status of an invoice"""
    params = {
        "invoice_ids": str(invoice_id)
    }
    
    result, error = await crypto_pay_request("getInvoices", params)
    
    if error:
        return None, error
    
    if result and result.get("items"):
        return result["items"][0], None
    
    return None, "Invoice not found"


# Crypto payment selection handler
@Client.on_callback_query(filters.regex(r"^crypto_pay_"))
async def crypto_payment_handler(client: Client, query):
    """Handle crypto payment requests"""
    data = query.data
    user_id = query.from_user.id
    
    # Check if Crypto Pay is configured
    if not CRYPTO_PAY_API_TOKEN:
        await query.answer("❌ Crypto payments not configured! Contact admin.", show_alert=True)
        return
    
    if data.startswith("crypto_pay_"):
        plan = data.replace("crypto_pay_", "")  # 1day, 7day, 30day
        
        # Get USD pricing
        amount_usd = await db.get_global_setting(f'pricing_{plan}_usd', 0.15)
        days = PLAN_DURATIONS.get(plan, 1)
        
        # Show processing message
        await query.message.edit_text("⏳ **Creating crypto invoice...**\n\nPlease wait...")
        
        # Create invoice
        invoice, error = await create_crypto_invoice(user_id, plan, amount_usd)
        
        if error:
            await query.message.edit_text(
                f"❌ **Failed to create invoice**\n\n"
                f"Error: {error}\n\n"
                f"Please try again or contact admin.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data=f"premium_payment_{plan}")
                ]])
            )
            return
        
        # Store invoice in database
        invoice_id = invoice.get("invoice_id")
        pay_url = invoice.get("bot_invoice_url") or invoice.get("pay_url")
        
        await db.create_crypto_invoice(
            invoice_id=invoice_id,
            user_id=user_id,
            plan=plan,
            amount=amount_usd,
            asset="MULTI",  # Multiple assets accepted
            pay_url=pay_url
        )
        
        # Build payment message
        text = f"""**💰 Crypto Payment**

**Plan:** {days} Day(s) Premium
**Amount:** ${amount_usd} USDT

━━━━━━━━━━━━━━━━━━━━━━━━

> **⚠️ Important:**
> Make sure you have **at least $1** balance in @CryptoBot before making a payment. Smaller amounts may not be processed correctly.

━━━━━━━━━━━━━━━━━━━━━━━━

> **📝 How to Pay:**
> 
> 1. Click "💳 Pay Now" button below
> 2. Pay with USDT from your @CryptoBot wallet
> 3. Premium activates automatically!

━━━━━━━━━━━━━━━━━━━━━━━━

**Invoice ID:** `{invoice_id}`
**Expires:** 1 hour

✅ After payment, click "Check Payment" to verify."""

        buttons = [
            [InlineKeyboardButton("💳 Pay Now", url=pay_url)],
            [InlineKeyboardButton("✅ Check Payment", callback_data=f"check_crypto_{invoice_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data=f"premium_payment_{plan}")]
        ]
        
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    await query.answer()


# Check payment status
@Client.on_callback_query(filters.regex(r"^check_crypto_"))
async def check_crypto_payment(client: Client, query):
    """Check if crypto payment was completed"""
    invoice_id = int(query.data.replace("check_crypto_", ""))
    user_id = query.from_user.id
    
    await query.answer("⏳ Checking payment status...", show_alert=False)
    
    # Get invoice from database
    db_invoice = await db.get_crypto_invoice(invoice_id)
    
    if not db_invoice:
        await query.answer("❌ Invoice not found!", show_alert=True)
        return
    
    if db_invoice.get("user_id") != user_id:
        await query.answer("❌ This invoice doesn't belong to you!", show_alert=True)
        return
    
    # Check if already processed
    if db_invoice.get("status") == "paid":
        await query.answer("✅ This payment was already processed!", show_alert=True)
        return
    
    # Check status with Crypto Pay API
    invoice, error = await check_invoice_status(invoice_id)
    
    if error:
        await query.answer(f"❌ Error: {error}", show_alert=True)
        return
    
    status = invoice.get("status")
    
    if status == "paid":
        # Payment successful! Activate premium
        plan = db_invoice.get("plan")
        days = PLAN_DURATIONS.get(plan, 1)
        
        # Calculate expiry
        duration = days * 24 * 60 * 60  # Convert to seconds
        
        # Check if user already has premium
        user = await db.col.find_one({'id': user_id})
        is_premium_user = await db.is_premium(user_id)
        
        if is_premium_user and user.get('premium_expiry'):
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
        
        # Get payment details
        paid_amount = invoice.get("paid_amount", invoice.get("amount"))
        paid_asset = invoice.get("paid_asset", "crypto")
        
        from datetime import datetime
        expiry_date = datetime.fromtimestamp(expiry_time).strftime('%Y-%m-%d %H:%M:%S')
        
        success_text = f"""
✅ **Payment Successful!**

**Amount Paid:** {paid_amount} {paid_asset}
**Plan:** {days} Day(s) Premium
**Expires:** {expiry_date}

**Your Benefits:**
• ✅ Unlimited downloads per day
• ✅ Priority support
• ✅ Faster processing

Thank you for your purchase! 🎉
"""
        
        buttons = [[InlineKeyboardButton("🏠 Main Menu", callback_data="start")]]
        await query.message.edit_text(success_text, reply_markup=InlineKeyboardMarkup(buttons))
        
    elif status == "expired":
        await db.update_crypto_invoice_status(invoice_id, "expired")
        await query.answer("❌ This invoice has expired. Please create a new one.", show_alert=True)
        
    elif status == "active":
        await query.answer("⏳ Payment not yet received. Please complete the payment first.", show_alert=True)
    
    else:
        await query.answer(f"⚠️ Invoice status: {status}", show_alert=True)


# Admin command to check Crypto Pay status
@Client.on_message(filters.command("cryptostatus") & filters.private & filters.user(ADMINS))
async def crypto_status(client: Client, message: Message):
    """Check Crypto Pay API status and balance"""
    
    if not CRYPTO_PAY_API_TOKEN:
        return await message.reply("❌ **Crypto Pay API token not configured!**\n\nSet `CRYPTO_PAY_API_TOKEN` in config.")
    
    # Test API connection
    result, error = await crypto_pay_request("getMe")
    
    if error:
        return await message.reply(f"❌ **API Error:** {error}")
    
    app_name = result.get("name", "Unknown")
    app_id = result.get("app_id", "Unknown")
    
    # Get balance
    balance_result, balance_error = await crypto_pay_request("getBalance")
    
    balance_text = ""
    if balance_result:
        for bal in balance_result:
            if float(bal.get("available", 0)) > 0:
                balance_text += f"• {bal.get('currency_code')}: {bal.get('available')}\n"
    
    if not balance_text:
        balance_text = "No balance"
    
    mode = "🧪 TESTNET" if CRYPTO_PAY_TESTNET else "🔴 MAINNET"
    
    await message.reply(f"""**💰 Crypto Pay Status**

**Mode:** {mode}
**App Name:** {app_name}
**App ID:** {app_id}

**Balance:**
{balance_text}

**API URL:** `{CRYPTO_PAY_API_URL}`
""")


# Admin command to view crypto payment history
@Client.on_message(filters.command("cryptopayments") & filters.private & filters.user(ADMINS))
async def crypto_payments_list(client: Client, message: Message):
    """View recent crypto payments with user info and status"""
    
    result, error = await crypto_pay_request("getInvoices", {"count": 20})
    
    if error:
        return await message.reply(f"❌ **Error:** {error}")
    
    invoices = result.get("items", [])
    
    if not invoices:
        return await message.reply("📭 **No crypto invoices found.**")
    
    # Count by status
    paid_count = sum(1 for inv in invoices if inv.get("status") == "paid")
    pending_count = sum(1 for inv in invoices if inv.get("status") == "active")
    expired_count = sum(1 for inv in invoices if inv.get("status") == "expired")
    
    text = f"""**💰 Crypto Payment History**

**Summary:**
✅ Paid: {paid_count} | ⏳ Pending: {pending_count} | ❌ Expired: {expired_count}

**Recent Invoices:**
"""
    
    for inv in invoices[:15]:
        status = inv.get("status", "unknown")
        if status == "paid":
            status_emoji = "✅"
            status_text = "PAID"
        elif status == "active":
            status_emoji = "⏳"
            status_text = "PENDING"
        elif status == "expired":
            status_emoji = "❌"
            status_text = "EXPIRED"
        else:
            status_emoji = "❓"
            status_text = status.upper()
        
        amount = inv.get("amount")
        asset = inv.get("asset", "USDT")
        inv_id = inv.get("invoice_id")
        
        # Get user ID from payload
        payload = inv.get("payload", "")
        if ":" in payload:
            user_id = payload.split(":")[0]
        else:
            user_id = "Unknown"
        
        # Get paid amount if paid
        paid_info = ""
        if status == "paid":
            paid_amount = inv.get("paid_amount", amount)
            paid_asset = inv.get("paid_asset", asset)
            paid_info = f" → {paid_amount} {paid_asset}"
        
        text += f"{status_emoji} `{inv_id}` | User: `{user_id}` | {amount} {asset}{paid_info} | {status_text}\n"
    
    text += f"\n**Total Invoices:** {len(invoices)}"
    
    await message.reply(text)
