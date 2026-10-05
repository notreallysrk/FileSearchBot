# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
STRINGS = {
    'welcome_text': (
        "🔞 <b>Welcome to 18+ Media Search</b>\n\n"
        "Send any model name, video title, or studio to find files!\n\n"
        "<b>Commands:</b>\n"
        "• /explore - Browse library\n"
        "• /random - Get random videos\n"
        "• /request - Request missing media\n"
        "• /help - Help & command list"
    ),
    'welcome_dual_text': (
        "🔞 <b>Welcome to 18+ Media Search</b>\n\n"
        "Send any model name, video title, or studio to find files!\n"
        "Files are delivered securely via @{delivery_username}\n\n"
        "<b>Commands:</b>\n"
        "• /explore - Browse library\n"
        "• /random - Get random videos\n"
        "• /request - Request missing media\n"
        "• /help - Help & command list"
    ),
    'help_text': (
        "📖 <b>Help Menu</b>\n\n"
        "<b>Commands:</b>\n"
        "• /start - Start the bot\n"
        "• /explore - Browse library\n"
        "• /random [n] - Get up to 10 random videos\n"
        "• /request [title] - Request missing media\n"
        "• #request [title] - Request using hashtag\n"
        "• /lang - Change language\n"
        "• /cancel - Cancel active operation\n\n"
        "Tap 🎬, 📃, 📷, or 🎵 below search results to filter files."
    ),
    'help_text_owner': (
        "📖 <b>Help Menu (Owner)</b>\n\n"
        "<b>User Commands:</b>\n"
        "• /start, /explore, /random, /request, #request, /lang, /cancel\n\n"
        "<b>Admin Commands:</b>\n"
        "• /stats - Hardware & system info\n"
        "• /scan &lt;start&gt;-&lt;end&gt; - Scan channel\n"
        "• /allow &lt;chat_id&gt; - Allow group for indexing\n"
        "• /disallow &lt;chat_id&gt; - Disallow group\n"
        "• /allowed - List allowed indexing groups\n"
        "• /vars - View environment variables\n"
        "• /setvar &lt;name&gt; &lt;val&gt; - Update variable\n"
        "• /maintain &lt;on|off&gt; - Maintenance mode\n"
        "• /restart - Reboot bot\n"
        "• /block, /unblock, /blocked - Manage users"
    ),
    'group_restricted': (
        "⚠️ <b>Private Chat Only</b>\n\n"
        "This bot works only in private chat for security.\n"
        "Click below to start searching privately."
    ),
    'group_usage_guide': (
        "👋 <b>Bot Usage Guide</b>\n\n"
        "• Search files: <code>/search &lt;name&gt;</code>\n"
        "• Request files: <code>/request &lt;name&gt;</code> or <code>#request &lt;name&gt;</code>\n"
        "• Downloads & full library: in Bot PM"
    ),
    'btn_open_pm': "🚀 Open in Private Chat",
    'btn_support_group': "📢 Support Group",
    'btn_backup_channel': "🔗 Backup Channel",
    'btn_help': "📖 Help",
    'btn_back': "🔙 Back",
    'lang_choose': "🌐 <b>Choose your preferred language / अपनी पसंदीदा भाषा चुनें:</b>",
    'lang_updated': "✅ <b>Language successfully updated to English!</b>",
    'btn_lang_en': "🇬🇧 English",
    'btn_lang_hi': "🇮🇳 हिन्दी",
    'force_sub_prompt': (
        "👋 <b>Subscription Required</b>\n\n"
        "Please join our update channels below and tap <b>Confirm Joining</b> to access files."
    ),
    'btn_join_channel': "📢 Join Channel",
    'btn_confirm_sub': "✅ Confirm Joining",
    'sub_still_missing': "⚠️ You haven't joined all required channels yet. Please join and tap Confirm!",
    'force_sub_still_missing': "⚠️ Please join all channels before verifying!",
    'force_sub_verified': "✅ Verified! Welcome.",
    'search_too_short': "⚠️ Query is too short! Please type at least 2 characters.",
    'search_too_long': "⚠️ Query is too long! Please keep it under 100 characters.",
    'search_no_results': (
        "🔞 <b>No Media Found</b>\n\n"
        "No files matching: <i>{query}</i>\n"
        "Check spelling or tap Request below to request it."
    ),
    'btn_request_file': "🔞 Request This Video",
    'search_results_header': (
        "🔍 <b>Results for:</b> <code>{query}</code>\n"
        "Found <b>{total}</b> file(s) (Page {page}/{pages}):\n\n"
        "<i>👇 Tap any button below to download:</i>"
    ),
    'btn_prev': "⬅️ Prev",
    'btn_next': "Next ➡️",
    'session_expired': "⚠️ Search session expired. Please send your query again.",
    'session_not_yours': "⛔ This search session belongs to another user.",
    'file_delivery_dual_redirect': (
        "📦 <b>File Ready</b>\n\n"
        "Files are delivered via our Delivery Bot.\n"
        "<a href='{url}'>Tap here to retrieve on @{delivery_username}</a>"
    ),
    'file_delivery_caption': (
        "📁 <b>{file_name}</b>\n"
        "📦 Size: <code>{file_size}</code>\n\n"
        "⏳ <i>Auto-deletes in 5 minutes! Save or forward now.</i>"
    ),
    'delivery_delete_notice': "\n\n⏳ <i>Auto-deletes in 5 minutes! Save or forward now.</i>",
    'delivery_invalid_token': "The download link is invalid or malformed.",
    'delivery_expired_token': "This download link has expired. Please search again.",
    'delivery_file_missing': "The requested file is no longer available in the index.",
    'delivery_user_blocked': "⛔ Your account has been suspended from downloading files.",
    'btn_back_to_search': "🔍 Back to Search",
    'btn_random_dual': "🎲 Get {count} Random Files",
    'random_dual_redirect': (
        "⚡ <b>Random Delivery Ready!</b>\n\n"
        "Click below to retrieve your random files via our Delivery Bot:"
    ),
    'delivery_agent_welcome': (
        "👋 Hello <b>{first_name}</b>!\n\n"
        "I am the <b>File Delivery Agent</b> for @{master_username}.\n"
        "I securely send requested files to your chat when you click a result link.\n\n"
        "Visit the <b>Master Bot</b> below to search:"
    ),
    'delivery_plain_text': (
        "ℹ️ <b>File Searching is handled by Master Bot</b>\n\n"
        "Please visit @{master_username} to search and download files!"
    ),
    'delivery_random_success': "✅ Delivered <b>{count}</b> random file(s).",
    'request_pm_only': "File requests can only be submitted in private chat.",
    'request_prompt': (
        "🔞 <b>Request Media</b>\n\n"
        "Send model name, studio, or video title.\n"
        "<i>Example:</i> <code>Sweetie Fox 1080p</code>\n"
        "Send <b>/cancel</b> to abort."
    ),
    'request_cancel_no_active': "There is no active operation to cancel.",
    'request_cancelled': "❌ Operation cancelled.",
    'request_text_only': "⚠️ Please send text or /cancel to abort.",
    'request_too_short': "⚠️ Description is too short (min 3 chars).",
    'request_too_long': "⚠️ Description is too long (max 300 chars).",
    'request_submitted': (
        "✅ <b>Request Received</b>\n\n"
        "• <b>Content:</b> {description}\n"
        "• <b>ID:</b> <code>{request_id}</code>\n\n"
        "You will be notified once uploaded!"
    ),
    'request_completed_notify': (
        "🎉 <b>Video Ready!</b>\n\n"
        "<b>Requested Video:</b> {description}\n\n"
        "You can now search for it!"
    ),
    'request_logger_new': (
        "📥 <b>New File Request</b>\n\n"
        "• <b>User:</b> {user_display} (<code>{user_id}</code>)\n"
        "{uname_line}"
        "• <b>Content:</b> {clean_desc}\n"
        "• <b>ID:</b> <code>{req_id}</code>"
    ),
    'request_logger_completed': (
        "✅ <b>Request Completed</b>\n\n"
        "• <b>User:</b> <code>{user_id}</code>\n"
        "• <b>Content:</b> {clean_desc}\n"
        "• <b>By:</b> <code>{completed_by_id}</code>"
    ),
    'request_btn_mark_uploaded': "✅ Mark Uploaded",
    'request_not_found_or_done': "This request does not exist or has already been completed.",
    'request_marked_success': "Request marked as uploaded and user notified!",
    'user_blocked': "⛔ <b>Access Denied</b>\nYou have been blocked from using this bot.",
    'user_unblocked': "✅ <b>Access Restored</b>\nYou can now use the bot again.",
    'maintenance_notice': (
        "🛠️ <b>Maintenance Mode</b>\n\n"
        "The bot is undergoing scheduled maintenance.\n"
        "We will be back shortly!"
    ),
    'btn_support_channel': "📢 Support Channel",
    'flood_warning': "⚠️ Slow down! You are sending requests too quickly.",
    'internal_error': "⚠️ An unexpected error occurred. Please try again later.",
    'admin_unauthorized': "⛔ You are not authorized to use this command.",
    'admin_maintain_usage': "Usage: <code>/maintain on</code> or <code>/maintain off</code>",
    'admin_maintain_enabled': "🛠️ Maintenance mode <b>ENABLED</b>. Public access is restricted.",
    'admin_maintain_disabled': "✅ Maintenance mode <b>DISABLED</b>. Public access restored.",
    'admin_maintain_status': "🛠️ Maintenance mode status: <code>{status}</code>",
    'admin_restart_notice': "🔄 <b>Restarting Bot Process...</b> (OS: <code>{platform}</code>)",
    'admin_block_usage': "Usage: <code>/block &lt;user_id&gt; [reason]</code>",
    'admin_block_cannot_self': "⚠️ You cannot block yourself or other owners.",
    'admin_block_already': "ℹ️ User <code>{user_id}</code> is already blocked.",
    'admin_block_success': "🚫 User <code>{user_id}</code> has been blocked.",
    'admin_unblock_usage': "Usage: <code>/unblock &lt;user_id&gt;</code>",
    'admin_unblock_not_found': "ℹ️ User <code>{user_id}</code> is not blocked.",
    'admin_unblock_success': "✅ User <code>{user_id}</code> has been unblocked.",
    'admin_blocked_empty': "📋 No users are currently blocked.",
    'admin_blocked_header': "📋 <b>Blocked Users ({count}):</b>\n",
    'admin_blocked_footer': "\n<i>Use /unblock &lt;user_id&gt; to unban</i>",
    'admin_vars_header': "📋 <b>Environment Variables:</b>\n",
    'admin_vars_footer': "\n<i>Use /setvar &lt;KEY&gt; &lt;VALUE&gt; to update</i>",
    'admin_setvar_usage': "Usage: <code>/setvar &lt;KEY&gt; &lt;VALUE&gt;</code>",
    'admin_setvar_success': "✅ <code>{var_name}</code> updated to <code>{masked}</code>. Restarting...",
    'admin_allow_usage': "⚠️ Usage: <code>/allow &lt;chat_id&gt;</code> (or run in target group)",
    'admin_allow_success': "✅ Group <code>{chat_id}</code> added to allowed indexing list.",
    'admin_allow_exists': "⚠️ Group <code>{chat_id}</code> is already in allowed list.",
    'admin_disallow_usage': "⚠️ Usage: <code>/disallow &lt;chat_id&gt;</code> (or run in target group)",
    'admin_disallow_success': "🗑️ Group <code>{chat_id}</code> removed from allowed indexing list.",
    'admin_disallow_not_found': "⚠️ Group <code>{chat_id}</code> was not in allowed list.",
    'admin_allowed_header': "📋 <b>Allowed Groups for File Indexing:</b>\n",
    'admin_allowed_footer': "\n<i>Only media from these groups will be indexed in database.</i>",
    'admin_scan_private_error': "⚠️ <code>/scan</code> can only be used in groups and channels where files are stored.",
    'admin_scan_invalid_format': "⚠️ Usage: <code>/scan &lt;start_id&gt; &lt;end_id&gt;</code>",
    'admin_scan_already_running': "⚠️ A scan is already running for messages {start_id} to {end_id}.",
    'admin_scan_progress_template': (
        "📡 <b>Scan Progress:</b>\n\n"
        "• <b>Status:</b> {status}\n"
        "• <b>Progress:</b> {checked}/{total} ({pct:.1f}%)\n"
        "• <b>Files Saved:</b> {saved}\n"
        "• <b>Current ID:</b> <code>{current_id}</code>"
    ),
    'admin_scan_paused': "Scan paused.",
    'admin_scan_resumed': "Scan resumed.",
    'admin_scan_stopped': "Scan stopped.",
}
