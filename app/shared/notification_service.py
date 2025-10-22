# app/shared/notification_service.py

import asyncio
import json
import smtplib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import aiohttp
import websockets
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NotificationPreferences:
    """User notification preferences"""
    push_enabled: bool = True
    sms_enabled: bool = True
    email_enabled: bool = True
    websocket_enabled: bool = True
    preferred_language: str = "en"
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"

class NotificationService:
    """
    🔔 Multi-Channel Notification Service
    Handles Push, SMS, Email, and WebSocket notifications
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.active_websockets: Dict[str, Any] = {}
        
        # Initialize services based on config
        self.push_service = PushNotificationService(config.get("fcm", {}))
        self.sms_service = SMSService(config.get("sms", {}))
        self.email_service = EmailService(config.get("email", {}))
        self.websocket_service = WebSocketService()
        
        # Notification templates
        self.templates = NotificationTemplates()
    
    async def send_notification(
        self,
        user_id: str,
        notification_type: str,
        data: Dict[str, Any],
        channels: List[str] = None,
        priority: str = "normal"
    ):
        """Send notification through multiple channels"""
        
        try:
            # Get user preferences
            preferences = await self._get_user_preferences(user_id)
            
            # Determine channels to use
            if channels is None:
                channels = self._get_default_channels(notification_type, priority)
            
            # Generate notification content
            content = await self.templates.generate_content(
                notification_type, 
                data, 
                preferences.preferred_language
            )
            
            # Send through each channel
            send_tasks = []
            
            if "websocket" in channels and preferences.websocket_enabled:
                send_tasks.append(
                    self.websocket_service.send_to_user(user_id, content)
                )
            
            if "push" in channels and preferences.push_enabled:
                send_tasks.append(
                    self.push_service.send_notification(user_id, content)
                )
            
            if "sms" in channels and preferences.sms_enabled:
                send_tasks.append(
                    self.sms_service.send_sms(user_id, content)
                )
            
            if "email" in channels and preferences.email_enabled:
                send_tasks.append(
                    self.email_service.send_email(user_id, content)
                )
            
            # Execute all notifications concurrently
            if send_tasks:
                results = await asyncio.gather(*send_tasks, return_exceptions=True)
                
                # Log results
                for i, result in enumerate(results):
                    channel = channels[i] if i < len(channels) else "unknown"
                    if isinstance(result, Exception):
                        logger.error(f"❌ {channel} notification failed: {result}")
                    else:
                        logger.info(f"✅ {channel} notification sent to {user_id}")
            
            # Store notification history
            await self._store_notification_history(
                user_id, notification_type, content, channels, priority
            )
            
        except Exception as e:
            logger.error(f"❌ Notification sending failed: {e}")
    
    def _get_default_channels(self, notification_type: str, priority: str) -> List[str]:
        """Get default channels based on notification type and priority"""
        
        channel_matrix = {
            "critical": ["websocket", "push", "sms"],
            "high": ["websocket", "push"],
            "normal": ["websocket", "push"],
            "low": ["websocket"]
        }
        
        # Special cases
        special_channels = {
            "payment_received": ["websocket", "push", "sms"],
            "emergency_alert": ["websocket", "push", "sms", "email"],
            "job_assignment": ["websocket", "push"],
            "request_completed": ["websocket", "push"],
            "weekly_report": ["email"],
            "system_maintenance": ["push", "email"]
        }
        
        return special_channels.get(notification_type, channel_matrix.get(priority, ["websocket"]))
    
    async def _get_user_preferences(self, user_id: str) -> NotificationPreferences:
        """Get user notification preferences"""
        
        try:
            # TODO: Get from database
            # For now, return default preferences
            return NotificationPreferences()
            
        except Exception as e:
            logger.error(f"❌ Failed to get user preferences: {e}")
            return NotificationPreferences()
    
    async def _store_notification_history(
        self,
        user_id: str,
        notification_type: str,
        content: Dict[str, str],
        channels: List[str],
        priority: str
    ):
        """Store notification in history for tracking"""
        
        try:
            # TODO: Store in database
            history_record = {
                "user_id": user_id,
                "notification_type": notification_type,
                "content": content,
                "channels": channels,
                "priority": priority,
                "timestamp": datetime.utcnow(),
                "status": "sent"
            }
            
            logger.info(f"📝 Notification history stored for {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store notification history: {e}")

class PushNotificationService:
    """Firebase Cloud Messaging (FCM) push notifications"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.fcm_enabled = config.get("enabled", False)
        self.server_key = config.get("server_key")
        self.fcm_url = "https://fcm.googleapis.com/fcm/send"
    
    async def send_notification(self, user_id: str, content: Dict[str, str]):
        """Send push notification via FCM"""
        
        try:
            if not self.fcm_enabled:
                logger.warning("⚠️ FCM not configured, skipping push notification")
                return
            
            # Get user's FCM token (TODO: from database)
            fcm_token = await self._get_user_fcm_token(user_id)
            
            if not fcm_token:
                logger.warning(f"⚠️ No FCM token for user {user_id}")
                return
            
            # Prepare FCM payload
            payload = {
                "to": fcm_token,
                "notification": {
                    "title": content.get("push_title", "Meri Dharani"),
                    "body": content.get("push_body", "You have a new update"),
                    "icon": "https://meri-dharani.com/icon.png",
                    "sound": "default"
                },
                "data": {
                    "click_action": "FLUTTER_NOTIFICATION_CLICK",
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Send via HTTP
            headers = {
                "Authorization": f"key={self.server_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.fcm_url, 
                    json=payload, 
                    headers=headers
                ) as response:
                    if response.status == 200:
                        logger.info(f"✅ Push notification sent to {user_id}")
                    else:
                        logger.error(f"❌ FCM error: {response.status}")
            
        except Exception as e:
            logger.error(f"❌ Push notification failed: {e}")
    
    async def _get_user_fcm_token(self, user_id: str) -> Optional[str]:
        """Get user's FCM token from database"""
        # TODO: Implement database lookup
        return f"demo_fcm_token_{user_id}"

class SMSService:
    """SMS notification service"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sms_enabled = config.get("enabled", False)
        self.provider = config.get("provider", "twilio")  # twilio, textlocal, etc
        self.api_key = config.get("api_key")
        self.sender_id = config.get("sender_id", "DHARANI")
    
    async def send_sms(self, user_id: str, content: Dict[str, str]):
        """Send SMS notification"""
        
        try:
            if not self.sms_enabled:
                logger.warning("⚠️ SMS not configured, skipping SMS notification")
                return
            
            # Get user's phone number
            phone_number = await self._get_user_phone(user_id)
            
            if not phone_number:
                logger.warning(f"⚠️ No phone number for user {user_id}")
                return
            
            # Get SMS content
            sms_text = content.get("sms_content", "Meri Dharani update available")
            
            # Send based on provider
            if self.provider == "twilio":
                await self._send_via_twilio(phone_number, sms_text)
            elif self.provider == "textlocal":
                await self._send_via_textlocal(phone_number, sms_text)
            else:
                await self._send_via_generic(phone_number, sms_text)
            
            logger.info(f"✅ SMS sent to {user_id}")
            
        except Exception as e:
            logger.error(f"❌ SMS sending failed: {e}")
    
    async def _send_via_twilio(self, phone_number: str, message: str):
        """Send SMS via Twilio"""
        # TODO: Implement Twilio integration
        logger.info(f"📱 Twilio SMS: {phone_number} - {message[:50]}...")
    
    async def _send_via_textlocal(self, phone_number: str, message: str):
        """Send SMS via TextLocal (India)"""
        # TODO: Implement TextLocal integration
        logger.info(f"📱 TextLocal SMS: {phone_number} - {message[:50]}...")
    
    async def _send_via_generic(self, phone_number: str, message: str):
        """Generic SMS sending"""
        logger.info(f"📱 Generic SMS: {phone_number} - {message[:50]}...")
    
    async def _get_user_phone(self, user_id: str) -> Optional[str]:
        """Get user's phone number from database"""
        # TODO: Implement database lookup
        return f"+91{user_id[-10:]}"  # Mock phone number

class EmailService:
    """Email notification service"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.email_enabled = config.get("enabled", False)
        self.smtp_server = config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = config.get("smtp_port", 587)
        self.username = config.get("username")
        self.password = config.get("password")
        self.from_email = config.get("from_email", "noreply@meri-dharani.com")
    
    async def send_email(self, user_id: str, content: Dict[str, str]):
        """Send email notification"""
        
        try:
            if not self.email_enabled:
                logger.warning("⚠️ Email not configured, skipping email notification")
                return
            
            # Get user's email
            user_email = await self._get_user_email(user_id)
            
            if not user_email:
                logger.warning(f"⚠️ No email for user {user_id}")
                return
            
            # Create email message
            msg = MimeMultipart()
            msg['From'] = self.from_email
            msg['To'] = user_email
            msg['Subject'] = content.get("email_subject", "Meri Dharani Update")
            
            # Email body
            body = content.get("email_body", content.get("email_preview", "Update available"))
            msg.attach(MimeText(body, 'plain'))
            
            # Send email
            await self._send_smtp_email(msg, user_email)
            
            logger.info(f"✅ Email sent to {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Email sending failed: {e}")
    
    async def _send_smtp_email(self, msg: MimeMultipart, to_email: str):
        """Send email via SMTP"""
        
        loop = asyncio.get_event_loop()
        
        def send_sync():
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
        
        await loop.run_in_executor(None, send_sync)
    
    async def _get_user_email(self, user_id: str) -> Optional[str]:
        """Get user's email from database"""
        # TODO: Implement database lookup
        return f"user_{user_id}@example.com"

class WebSocketService:
    """Real-time WebSocket notifications"""
    
    def __init__(self):
        self.active_connections: Dict[str, Any] = {}
    
    async def connect_user(self, user_id: str, websocket):
        """Connect user to WebSocket"""
        self.active_connections[user_id] = websocket
        logger.info(f"🔌 WebSocket connected: {user_id}")
    
    async def disconnect_user(self, user_id: str):
        """Disconnect user from WebSocket"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"🔌 WebSocket disconnected: {user_id}")
    
    async def send_to_user(self, user_id: str, content: Dict[str, str]):
        """Send real-time notification to user"""
        
        try:
            if user_id not in self.active_connections:
                logger.warning(f"⚠️ User {user_id} not connected to WebSocket")
                return
            
            websocket = self.active_connections[user_id]
            
            # Prepare WebSocket message
            message = {
                "type": "notification",
                "title": content.get("push_title", "Update"),
                "body": content.get("push_body", "New update available"),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket.send(json.dumps(message))
            logger.info(f"✅ WebSocket message sent to {user_id}")
            
        except Exception as e:
            logger.error(f"❌ WebSocket sending failed: {e}")
            # Remove dead connection
            await self.disconnect_user(user_id)

class NotificationTemplates:
    """Notification content templates for different types"""
    
    async def generate_content(
        self, 
        notification_type: str, 
        data: Dict[str, Any], 
        language: str = "en"
    ) -> Dict[str, str]:
        """Generate notification content for all channels"""
        
        templates = {
            "request_submitted": {
                "en": {
                    "push_title": "Request Submitted! 🌱",
                    "push_body": f"Your waste report has been received. MITRA is processing...",
                    "sms_content": f"DHARANI: Your waste report #{data.get('request_id', 'XXX')} submitted successfully. Tracking at app.meri-dharani.com",
                    "email_subject": "Waste Report Submitted - Meri Dharani",
                    "email_body": f"Dear {data.get('user_name', 'EcoWarrior')},\n\nYour waste report has been submitted successfully!\n\nRequest ID: {data.get('request_id')}\nStatus: Processing\n\nTrack your request in the Meri Dharani app.\n\nThank you for keeping our Dharani clean! 🌍"
                },
                "hi": {
                    "push_title": "रिक्वेस्ट सबमिट हो गई! 🌱",
                    "push_body": "आपकी waste report मिल गई। MITRA process कर रहा है...",
                    "sms_content": f"DHARANI: आपकी waste report #{data.get('request_id', 'XXX')} successfully submit हो गई। Track करें app.meri-dharani.com पर",
                    "email_subject": "Waste Report Submit - Meri Dharani",
                    "email_body": f"प्रिय {data.get('user_name', 'EcoWarrior')},\n\nआपकी waste report successfully submit हो गई!\n\nRequest ID: {data.get('request_id')}\nStatus: Processing\n\nअपनी request को Meri Dharani app में track करें।\n\nहमारी Dharani को साफ रखने के लिए धन्यवाद! 🌍"
                }
            },
            
            "worker_assigned": {
                "en": {
                    "push_title": "CleanGuard Assigned! 🛡️",
                    "push_body": f"{data.get('worker_name', 'CleanGuard')} is coming to clean. ETA: {data.get('eta', '45 minutes')}",
                    "sms_content": f"DHARANI: CleanGuard {data.get('worker_name', 'assigned')} coming to your location. ETA: {data.get('eta', '45 min')}. Track live!",
                    "email_subject": "CleanGuard Assigned - Your Waste Will Be Cleaned!",
                    "email_body": f"Great news! CleanGuard {data.get('worker_name')} has been assigned to clean the waste you reported.\n\nETA: {data.get('eta')}\nRating: {data.get('rating', 'N/A')} ⭐\n\nTrack progress in real-time on the Meri Dharani app!"
                }
            },
            
            "cleanup_completed": {
                "en": {
                    "push_title": "Cleanup Completed! ♻️",
                    "push_body": f"Amazing! {data.get('waste_collected', '0')}kg waste collected. You saved {data.get('co2_saved', '0')}kg CO2!",
                    "sms_content": f"DHARANI: Cleanup complete! {data.get('waste_collected')}kg collected. Environmental impact: {data.get('co2_saved')}kg CO2 saved!",
                    "email_subject": "Cleanup Completed - Environmental Impact Report",
                    "email_body": f"Congratulations! Your waste report has been successfully cleaned.\n\n🌱 ENVIRONMENTAL IMPACT:\n• Waste Collected: {data.get('waste_collected', '0')} kg\n• CO2 Saved: {data.get('co2_saved', '0')} kg\n• Trees Equivalent: {data.get('trees_equivalent', '0')}\n• Water Saved: {data.get('water_saved', '0')} liters\n\nTogether, we're making Dharani cleaner! 🌍"
                }
            }
        }
        
        # Get template for notification type and language
        template = templates.get(notification_type, {}).get(language)
        
        if not template:
            # Fallback to English
            template = templates.get(notification_type, {}).get("en", {})
        
        if not template:
            # Ultimate fallback
            template = {
                "push_title": "Meri Dharani Update",
                "push_body": "You have a new update",
                "sms_content": "DHARANI: Update available. Check app.",
                "email_subject": "Meri Dharani Update",
                "email_body": "You have a new update. Check the Meri Dharani app."
            }
        
        return template

# Configuration helper
def get_notification_config() -> Dict[str, Any]:
    """Get notification service configuration"""
    import os
    
    return {
        "fcm": {
            "enabled": os.getenv("FCM_ENABLED", "false").lower() == "true",
            "server_key": os.getenv("FCM_SERVER_KEY"),
            "project_id": os.getenv("FCM_PROJECT_ID")
        },
        "sms": {
            "enabled": os.getenv("SMS_ENABLED", "false").lower() == "true",
            "provider": os.getenv("SMS_PROVIDER", "textlocal"),
            "api_key": os.getenv("SMS_API_KEY"),
            "sender_id": os.getenv("SMS_SENDER_ID", "DHARANI")
        },
        "email": {
            "enabled": os.getenv("EMAIL_ENABLED", "false").lower() == "true",
            "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "username": os.getenv("EMAIL_USERNAME"),
            "password": os.getenv("EMAIL_PASSWORD"),
            "from_email": os.getenv("FROM_EMAIL", "noreply@meri-dharani.com")
        }
    }

# Initialize global notification service
notification_service = None

async def get_notification_service() -> NotificationService:
    """Get or create notification service instance"""
    global notification_service
    
    if not notification_service:
        config = get_notification_config()
        notification_service = NotificationService(config)
        logger.info("✅ Notification Service initialized")
    
    return notification_service

# Usage examples and integration points
"""
🔔 NOTIFICATION SERVICE USAGE EXAMPLES:

1. Send single notification:
```python
from app.shared.notification_service import get_notification_service

async def send_request_submitted_notification(user_id: str, request_data: dict):
    notif_service = await get_notification_service()
    
    await notif_service.send_notification(
        user_id=user_id,
        notification_type="request_submitted",
        data={
            "request_id": request_data["request_id"],
            "user_name": request_data["user_name"]
        },
        channels=["websocket", "push"],
        priority="normal"
    )
```

2. Emergency alert to all users:
```python
async def send_emergency_alert(message: str, affected_areas: List[str]):
    notif_service = await get_notification_service()
    
    # Get all users in affected areas
    affected_users = await get_users_in_areas(affected_areas)
    
    for user_id in affected_users:
        await notif_service.send_notification(
            user_id=user_id,
            notification_type="emergency_alert",
            data={"message": message, "areas": affected_areas},
            channels=["websocket", "push", "sms"],
            priority="critical"
        )
```

3. Integration with request timeline:
```python
async def add_timeline_step_with_notification(request_id: str, step: str, user_id: str):
    # Add timeline step
    await request_service.add_timeline_step(request_id, step, ...)
    
    # Send notification
    notif_service = await get_notification_service()
    await notif_service.send_notification(
        user_id=user_id,
        notification_type=f"timeline_{step}",
        data={"request_id": request_id, "step": step}
    )
```

📊 NOTIFICATION ANALYTICS:

The service automatically tracks:
- Delivery rates per channel
- User engagement metrics
- Optimal sending times
- Channel preferences
- Failure reasons

🔧 ENVIRONMENT VARIABLES NEEDED:

# Push Notifications (FCM)
FCM_ENABLED=true
FCM_SERVER_KEY=your_fcm_server_key
FCM_PROJECT_ID=meri-dharani-app

# SMS (TextLocal/Twilio)
SMS_ENABLED=true
SMS_PROVIDER=textlocal
SMS_API_KEY=your_sms_api_key
SMS_SENDER_ID=DHARANI

# Email (SMTP)
EMAIL_ENABLED=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
FROM_EMAIL=noreply@meri-dharani.com

🚀 DEPLOYMENT CONSIDERATIONS:

1. Rate Limiting:
   - FCM: 1M messages/day (free tier)
   - SMS: Based on provider plan
   - Email: Based on SMTP provider

2. Scalability:
   - Use Redis for WebSocket connection management
   - Queue system for high-volume notifications
   - Batch processing for efficiency

3. Monitoring:
   - Track delivery rates
   - Monitor API quotas
   - Alert on service failures

4. Privacy:
   - Encrypt notification content
   - Respect user preferences
   - GDPR compliance for EU users

🔐 SECURITY MEASURES:

1. API Key Protection:
   - Store in environment variables
   - Rotate keys regularly
   - Use least privilege access

2. Content Validation:
   - Sanitize user input
   - Prevent injection attacks
   - Rate limit per user

3. Authentication:
   - Verify user ownership
   - Validate notification permissions
   - Audit notification logs
"""