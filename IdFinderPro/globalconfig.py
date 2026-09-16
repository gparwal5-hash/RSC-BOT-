from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import db
from config import ADMINS

# State to track user input for global config
globalconfig_state = {}

@Client.on_message(filters.private & filters.command(["globalconfig"]) & filters.user(ADMINS))
async def globalconfig_menu(client: Client, message: Message):
    """Global configuration menu (admin only)"""
    settings = await db.get_all_global_settings()
    
    text = f"""**⚙️ Global Configuration**

Manage bot-wide settings and pricing.

**Current Settings:**
• **1 Day Price:** ₹{settings.get('pricing_1day', 10)}
• **7 Days Price:** ₹{settings.get('pricing_7day', 40)}
• **30 Days Price:** ₹{settings.get('pricing_30day', 100)}
• **Admin Handle:** {settings.get('admin_telegram_handle', '@tataa_sumo')}
• **Free Daily Limit:** {settings.get('free_daily_limit', 10)} downloads
• **Premium Daily Limit:** {settings.get('premium_daily_limit', 'Unlimited')}"""
    
    buttons = [
        [InlineKeyboardButton("💰 Edit Pricing", callback_data="gc_pricing")],
        [InlineKeyboardButton("👤 Edit Admin Handle", callback_data="gc_admin")],
        [InlineKeyboardButton("📊 Edit Limits", callback_data="gc_limits")],
        [InlineKeyboardButton("🏠 Back to Admin", callback_data="admin_panel")]
    ]
    
    await message.reply(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex(r"^gc_"))
async def globalconfig_callback_handler(client: Client, query):
    """Handle global config callbacks"""
    data = query.data
    user_id = query.from_user.id
    
    if data == "gc_pricing":
        settings = await db.get_all_global_settings()
        
        text = f"""**💰 Pricing Configuration**

**Current Prices:**
• **1 Day:** ₹{settings.get('pricing_1day', 10)}
• **7 Days:** ₹{settings.get('pricing_7day', 40)}
• **30 Days:** ₹{settings.get('pricing_30day', 100)}

Select which price to edit:"""
        
        buttons = [
            [InlineKeyboardButton("1 Day Price", callback_data="gc_edit_pricing_1day")],
            [InlineKeyboardButton("7 Days Price", callback_data="gc_edit_pricing_7day")],
            [InlineKeyboardButton("30 Days Price", callback_data="gc_edit_pricing_30day")],
            [InlineKeyboardButton("🔙 Back", callback_data="gc_menu")]
        ]
        
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data.startswith("gc_edit_pricing_"):
        plan = data.split("_")[-1]  # 1day, 7day, or 30day
        globalconfig_state[user_id] = {'action': 'edit_pricing', 'plan': plan}
        
        plan_name = plan.replace('day', ' Days' if 'day' in plan and plan[0] != '1' else ' Day')
        
        text = f"""**💰 Edit {plan_name} Price**

Please send the new price in rupees.

**Example:** `50`

Send /cancel to cancel."""
        
        buttons = [[InlineKeyboardButton("🔙 Back", callback_data="gc_pricing")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "gc_admin":
        settings = await db.get_all_global_settings()
        admin_handle = settings.get('admin_telegram_handle', '@tataa_sumo')
        
        globalconfig_state[user_id] = {'action': 'edit_admin'}
        
        text = f"""**👤 Edit Admin Telegram Handle**

**Current:** {admin_handle}

Please send the new admin Telegram handle.

**Example:** `@yourusername`

Send /cancel to cancel."""
        
        buttons = [[InlineKeyboardButton("🔙 Back", callback_data="gc_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "gc_limits":
        settings = await db.get_all_global_settings()
        
        text = f"""**📊 Download Limits**

**Current Settings:**
• **Free Users:** {settings.get('free_daily_limit', 10)} downloads/day
• **Premium Users:** {settings.get('premium_daily_limit', 999999)} downloads/day

Select which limit to edit:"""
        
        buttons = [
            [InlineKeyboardButton("Free User Limit", callback_data="gc_edit_limit_free")],
            [InlineKeyboardButton("Premium User Limit", callback_data="gc_edit_limit_premium")],
            [InlineKeyboardButton("🔙 Back", callback_data="gc_menu")]
        ]
        
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data.startswith("gc_edit_limit_"):
        limit_type = data.split("_")[-1]  # free or premium
        globalconfig_state[user_id] = {'action': 'edit_limit', 'type': limit_type}
        
        limit_name = "Free Users" if limit_type == "free" else "Premium Users"
        
        text = f"""**📊 Edit {limit_name} Download Limit**

Please send the new daily download limit.

**Example:** `20` (for 20 downloads per day)

**Note:** Use a very high number (e.g., 999999) for unlimited.

Send /cancel to cancel."""
        
        buttons = [[InlineKeyboardButton("🔙 Back", callback_data="gc_limits")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    elif data == "gc_menu":
        # Return to main globalconfig menu
        settings = await db.get_all_global_settings()
        
        text = f"""**⚙️ Global Configuration**

Manage bot-wide settings and pricing.

**Current Settings:**
• **1 Day Price:** ₹{settings.get('pricing_1day', 10)}
• **7 Days Price:** ₹{settings.get('pricing_7day', 40)}
• **30 Days Price:** ₹{settings.get('pricing_30day', 100)}
• **Admin Handle:** {settings.get('admin_telegram_handle', '@tataa_sumo')}
• **Free Daily Limit:** {settings.get('free_daily_limit', 10)} downloads
• **Premium Daily Limit:** {settings.get('premium_daily_limit', 'Unlimited')}"""
        
        buttons = [
            [InlineKeyboardButton("💰 Edit Pricing", callback_data="gc_pricing")],
            [InlineKeyboardButton("👤 Edit Admin Handle", callback_data="gc_admin")],
            [InlineKeyboardButton("📊 Edit Limits", callback_data="gc_limits")],
            [InlineKeyboardButton("🏠 Back to Admin", callback_data="admin_panel")]
        ]
        
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    await query.answer()

# Handle global config input
@Client.on_message(filters.private & filters.text & filters.user(ADMINS), group=22)
async def handle_globalconfig_input(client: Client, message: Message):
    """Handle global config input"""
    user_id = message.from_user.id
    
    if user_id not in globalconfig_state:
        return  # Not in globalconfig state
    
    if message.text == "/cancel":
        del globalconfig_state[user_id]
        return await message.reply("❌ **Cancelled.**")
    
    state = globalconfig_state[user_id]
    
    if state['action'] == 'edit_pricing':
        try:
            new_price = int(message.text.strip())
            
            if new_price < 1:
                return await message.reply("❌ **Invalid price!**\n\nPrice must be at least ₹1.")
            
            plan = state['plan']
            key = f"pricing_{plan}"
            
            await db.set_global_setting(key, new_price)
            del globalconfig_state[user_id]
            
            plan_name = plan.replace('day', ' Days' if 'day' in plan and plan[0] != '1' else ' Day')
            await message.reply(f"✅ **Price Updated!**\n\n**{plan_name}:** ₹{new_price}")
        
        except ValueError:
            await message.reply("❌ **Invalid input!**\n\nPlease send a number (e.g., 50)")
    
    elif state['action'] == 'edit_admin':
        admin_handle = message.text.strip()
        
        if not admin_handle.startswith('@'):
            return await message.reply("❌ **Invalid handle!**\n\nHandle must start with '@' (e.g., @username)")
        
        await db.set_global_setting('admin_telegram_handle', admin_handle)
        del globalconfig_state[user_id]
        
        await message.reply(f"✅ **Admin Handle Updated!**\n\n**New Handle:** {admin_handle}")
    
    elif state['action'] == 'edit_limit':
        try:
            new_limit = int(message.text.strip())
            
            if new_limit < 1:
                return await message.reply("❌ **Invalid limit!**\n\nLimit must be at least 1.")
            
            limit_type = state['type']
            key = f"{limit_type}_daily_limit"
            
            await db.set_global_setting(key, new_limit)
            del globalconfig_state[user_id]
            
            limit_name = "Free Users" if limit_type == "free" else "Premium Users"
            await message.reply(f"✅ **Limit Updated!**\n\n**{limit_name}:** {new_limit} downloads/day")
        
        except ValueError:
            await message.reply("❌ **Invalid input!**\n\nPlease send a number (e.g., 20)")
