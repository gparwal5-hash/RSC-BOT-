from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import db
from config import ADMINS

# State to track user input
upi_state = {}

@Client.on_message(filters.private & filters.command(["addupi"]) & filters.user(ADMINS))
async def addupi_menu(client: Client, message: Message):
    """UPI details management menu (admin only)"""
    upi_details = await db.get_upi_details()
    
    upi_id = upi_details['upi_id']
    receiver_name = upi_details['receiver_name']
    qr_file_id = upi_details['qr_file_id']
    
    if upi_id and receiver_name:
        status = "✅ Configured"
        upi_text = f"**UPI ID:** `{upi_id}`"
        name_text = f"**Receiver Name:** {receiver_name}"
        qr_text = "**QR Code:** Generated dynamically"
    else:
        status = "❌ Not Configured"
        upi_text = f"**UPI ID:** {'`' + upi_id + '`' if upi_id else 'Not set'}"
        name_text = f"**Receiver Name:** {receiver_name if receiver_name else 'Not set'}"
        qr_text = "**QR Code:** Generated dynamically"
    
    text = f"""**💳 UPI Payment Management**

**Status:** {status}

{upi_text}
{name_text}
{qr_text}

**Note:** QR codes are now generated dynamically for each transaction with exact amount and user ID."""
    
    buttons = [
        [InlineKeyboardButton("📝 Set UPI ID", callback_data="upi_set_id")],
        [InlineKeyboardButton("👤 Set Receiver Name", callback_data="upi_set_name")],
        [InlineKeyboardButton("👁️ View Details", callback_data="upi_view")],
        [InlineKeyboardButton("🗑️ Clear All", callback_data="upi_clear")],
        [InlineKeyboardButton("🏠 Back to Admin", callback_data="admin_panel")]
    ]
    
    await message.reply(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^upi_"))
async def upi_callback_handler(client: Client, query):
    """Handle UPI callbacks"""
    data = query.data
    user_id = query.from_user.id
    
    if data == "upi_set_id":
        upi_state[user_id] = {'action': 'set_id'}
        
        text = """**📝 Set UPI ID**

Please send your UPI ID.

**Examples:**
• `yourname@paytm`
• `9876543210@ybl`
• `username@oksbi`

Send /cancel to cancel."""
        
        buttons = [[InlineKeyboardButton("🔙 Back", callback_data="upi_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "upi_set_name":
        upi_state[user_id] = {'action': 'set_name'}
        
        text = """**👤 Set Receiver Name**

Please send the receiver name for UPI payments.

**Examples:**
• `John Doe`
• `Your Business Name`
• `Shop Name`

**Note:** This name will appear in the UPI payment request.

Send /cancel to cancel."""
        
        buttons = [[InlineKeyboardButton("🔙 Back", callback_data="upi_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "upi_view":
        upi_details = await db.get_upi_details()
        
        upi_id = upi_details['upi_id']
        receiver_name = upi_details['receiver_name']
        
        if not upi_id:
            await query.answer("❌ No UPI details configured!", show_alert=True)
            return
        
        text = f"""**💳 Current UPI Details**

**UPI ID:** `{upi_id}`
**Receiver Name:** {receiver_name if receiver_name else 'Not set'}

**QR Codes:** Generated dynamically for each transaction with exact amount and user ID."""
        
        buttons = [[InlineKeyboardButton("🔙 Back", callback_data="upi_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "upi_clear":
        await db.clear_upi_details()
        await query.answer("✅ UPI details cleared!", show_alert=True)
        
        # Return to menu
        text = """**💳 UPI Payment Management**

**Status:** ❌ Not Configured

**UPI ID:** Not set
**Receiver Name:** Not set
**QR Code:** Generated dynamically

**Note:** QR codes are now generated dynamically for each transaction with exact amount and user ID."""
        
        buttons = [
            [InlineKeyboardButton("📝 Set UPI ID", callback_data="upi_set_id")],
            [InlineKeyboardButton("👤 Set Receiver Name", callback_data="upi_set_name")],
            [InlineKeyboardButton("👁️ View Details", callback_data="upi_view")],
            [InlineKeyboardButton("🗑️ Clear All", callback_data="upi_clear")],
            [InlineKeyboardButton("🏠 Back to Admin", callback_data="admin_panel")]
        ]
        
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "upi_menu":
        # Return to UPI menu
        upi_details = await db.get_upi_details()
        
        upi_id = upi_details['upi_id']
        receiver_name = upi_details['receiver_name']
        
        if upi_id and receiver_name:
            status = "✅ Configured"
            upi_text = f"**UPI ID:** `{upi_id}`"
            name_text = f"**Receiver Name:** {receiver_name}"
        else:
            status = "❌ Not Configured"
            upi_text = f"**UPI ID:** {'`' + upi_id + '`' if upi_id else 'Not set'}"
            name_text = f"**Receiver Name:** {receiver_name if receiver_name else 'Not set'}"
        
        text = f"""**💳 UPI Payment Management**

**Status:** {status}

{upi_text}
{name_text}
**QR Code:** Generated dynamically

**Note:** QR codes are now generated dynamically for each transaction with exact amount and user ID."""
        
        buttons = [
            [InlineKeyboardButton("📝 Set UPI ID", callback_data="upi_set_id")],
            [InlineKeyboardButton("👤 Set Receiver Name", callback_data="upi_set_name")],
            [InlineKeyboardButton("👁️ View Details", callback_data="upi_view")],
            [InlineKeyboardButton("🗑️ Clear All", callback_data="upi_clear")],
            [InlineKeyboardButton("🏠 Back to Admin", callback_data="admin_panel")]
        ]
        
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    await query.answer()

# Handle UPI input (text only - no photo needed for dynamic QR)
@Client.on_message(filters.private & filters.user(ADMINS), group=21)
async def handle_upi_input(client: Client, message: Message):
    """Handle UPI input for ID and receiver name"""
    user_id = message.from_user.id
    
    if user_id not in upi_state:
        return  # Not in UPI state
    
    if message.text == "/cancel":
        del upi_state[user_id]
        return await message.reply("❌ **Cancelled.**")
    
    state = upi_state[user_id]
    
    if state['action'] == 'set_id':
        if not message.text:
            return await message.reply("❌ **Please send a text message with UPI ID!**")
        
        upi_id = message.text.strip()
        
        # Basic validation
        if '@' not in upi_id:
            return await message.reply("❌ **Invalid UPI ID!**\n\nUPI ID should contain '@' (e.g., name@paytm)")
        
        await db.set_upi_id(upi_id)
        del upi_state[user_id]
        
        await message.reply(f"✅ **UPI ID Set!**\n\n**UPI ID:** `{upi_id}`")
    
    elif state['action'] == 'set_name':
        if not message.text:
            return await message.reply("❌ **Please send a text message with receiver name!**")
        
        receiver_name = message.text.strip()
        
        if len(receiver_name) < 2:
            return await message.reply("❌ **Invalid name!**\n\nReceiver name should be at least 2 characters.")
        
        await db.set_receiver_name(receiver_name)
        del upi_state[user_id]
        
        await message.reply(f"✅ **Receiver Name Set!**\n\n**Receiver Name:** {receiver_name}")
