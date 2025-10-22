# app/shared/mitra_ai_service.py

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from groq import Groq
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MitraAIService:
    """
    🤖 MITRA - AI Assistant for Meri Dharani
    Provides personalized responses for different user types
    """
    
    def __init__(self, groq_api_key: str):
        self.groq_client = Groq(api_key=groq_api_key)
        self.model = "llama-3.3-70b-versatile"
        
        # Different personalities for different users
        self.personalities = {
            "citizen": {
                "name": "MITRA - EcoWarrior Assistant",
                "tone": "encouraging, friendly, environmental-focused",
                "language_mix": "Hindi + English mix for relatability",
                "emojis": True,
                "focus": "environmental impact, community building"
            },
            "worker": {
                "name": "MITRA - Professional Assistant", 
                "tone": "professional, helpful, earning-focused",
                "language_mix": "Simple Hindi + English",
                "emojis": True,
                "focus": "job efficiency, earnings, safety"
            },
            "government": {
                "name": "MITRA - Analytics Assistant",
                "tone": "formal, data-driven, actionable",
                "language_mix": "English primarily",
                "emojis": False,
                "focus": "data insights, policy recommendations"
            }
        }
    
    async def generate_timeline_message(
        self, 
        user_type: str, 
        step: str, 
        context: Dict[str, Any] = None
    ) -> str:
        """Generate AI message for timeline step"""
        
        try:
            personality = self.personalities.get(user_type, self.personalities["citizen"])
            
            # Create context-aware prompt
            prompt = self._create_timeline_prompt(user_type, step, context, personality)
            
            # Generate response using Groq
            chat_completion = await self._call_groq_async(prompt)
            
            ai_message = chat_completion.choices[0].message.content.strip()
            
            # Add processing time simulation
            processing_time = self._simulate_processing_time(step)
            await asyncio.sleep(processing_time)
            
            logger.info(f"✅ MITRA response generated for {user_type} - {step}")
            return ai_message
            
        except Exception as e:
            logger.error(f"❌ MITRA error: {e}")
            return self._get_fallback_message(user_type, step)
    
    def _create_timeline_prompt(
        self, 
        user_type: str, 
        step: str, 
        context: Dict[str, Any], 
        personality: Dict[str, str]
    ) -> str:
        """Create context-aware prompt for AI response"""
        
        base_context = f"""
        You are MITRA, the AI assistant for Meri Dharani waste management system.
        
        User Type: {user_type}
        Current Step: {step}
        Personality: {personality['tone']}
        Language Style: {personality['language_mix']}
        Use Emojis: {personality['emojis']}
        Focus Area: {personality['focus']}
        
        Context: {json.dumps(context) if context else 'No additional context'}
        
        Generate a brief, engaging message (max 100 characters) for this timeline step.
        """
        
        # Step-specific prompts
        step_prompts = {
            "citizen": {
                "submitted": "User just submitted a waste report. Welcome them warmly!",
                "ai_analyzing": "AI is analyzing their uploaded images. Show technical progress!",
                "worker_matching": "Finding the best CleanGuard for their location.",
                "worker_assigned": "CleanGuard has been assigned! Share worker details enthusiastically.",
                "en_route": "Worker is coming to location. Build excitement!",
                "cleanup_started": "Cleanup work has begun. Appreciate their contribution!",
                "completed": "Job completed successfully! Celebrate environmental impact!"
            },
            "worker": {
                "job_available": "New earning opportunity available! Share job details.",
                "job_accepted": "Job accepted! Provide navigation and safety tips.",
                "arrived": "Arrived at location! Guide through documentation process.",
                "cleanup_progress": "Work in progress! Encourage efficiency and quality.",
                "completed": "Job completed! Celebrate earnings and rating.",
                "payment_credited": "Payment processed! Thank for service."
            },
            "government": {
                "daily_summary": "Provide data-driven daily performance summary.",
                "efficiency_update": "Share efficiency metrics and trends.",
                "alert_generated": "Important system alert requiring attention.",
                "budget_update": "Budget utilization and resource allocation update.",
                "policy_recommendation": "AI-generated policy suggestion based on data."
            }
        }
        
        specific_prompt = step_prompts.get(user_type, {}).get(step, "General update message")
        
        return f"{base_context}\n\nSpecific Task: {specific_prompt}"
    
    async def _call_groq_async(self, prompt: str) -> Any:
        """Async wrapper for Groq API call"""
        
        loop = asyncio.get_event_loop()
        
        def sync_groq_call():
            return self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are MITRA, the friendly AI assistant for Meri Dharani waste management system. Always respond in the specified tone and language style."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                model=self.model,
                max_tokens=150,
                temperature=0.7
            )
        
        return await loop.run_in_executor(None, sync_groq_call)
    
    def _simulate_processing_time(self, step: str) -> float:
        """Simulate realistic AI processing time"""
        
        processing_times = {
            "submitted": 0.5,
            "ai_analyzing": 2.0,  # Longer for image analysis
            "worker_matching": 1.5,
            "worker_assigned": 0.5,
            "en_route": 0.3,
            "cleanup_started": 0.5,
            "completed": 1.0,
            "default": 0.5
        }
        
        return processing_times.get(step, processing_times["default"])
    
    def _get_fallback_message(self, user_type: str, step: str) -> str:
        """Fallback messages when AI fails"""
        
        fallback_messages = {
            "citizen": {
                "submitted": "🌱 MITRA: Request received! Processing...",
                "ai_analyzing": "🤖 MITRA: Analyzing images...", 
                "worker_matching": "🔍 MITRA: Finding CleanGuard...",
                "completed": "✅ MITRA: Great job! Dharani thanks you!"
            },
            "worker": {
                "job_available": "🔔 MITRA: New job available!",
                "job_accepted": "✅ MITRA: Job accepted! Navigate to location.",
                "completed": "💰 MITRA: Payment credited! Well done!"
            },
            "government": {
                "daily_summary": "📊 MITRA: Daily report ready.",
                "efficiency_update": "📈 MITRA: Performance metrics updated."
            }
        }
        
        return fallback_messages.get(user_type, {}).get(
            step, 
            f"🤖 MITRA: {step.replace('_', ' ').title()} update"
        )
    
    async def analyze_waste_image(self, image_data: Any) -> Dict[str, Any]:
        """Analyze waste image and return classification"""
        
        try:
            # Simulate AI image analysis
            await asyncio.sleep(2.0)  # Realistic processing time
            
            # For demo, return mock analysis
            # TODO: Integrate with actual computer vision model
            mock_analysis = {
                "waste_type": "plastic",
                "confidence": 0.87,
                "quantity_estimate": "2.5 kg",
                "recyclable": True,
                "priority": "medium",
                "suggested_tools": ["gloves", "pickup_stick", "sorting_bag"],
                "estimated_value": "₹15-25",
                "processing_time": 2.0
            }
            
            return mock_analysis
            
        except Exception as e:
            logger.error(f"❌ Image analysis error: {e}")
            return {
                "waste_type": "mixed",
                "confidence": 0.5,
                "quantity_estimate": "Unknown",
                "recyclable": False,
                "priority": "low",
                "error": str(e)
            }
    
    async def generate_notification_content(
        self, 
        user_type: str, 
        notification_type: str, 
        data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate notification content for different channels"""
        
        try:
            prompt = f"""
            Generate notification content for {user_type} user:
            
            Notification Type: {notification_type}
            Data: {json.dumps(data)}
            
            Generate:
            1. Push notification title (max 50 chars)
            2. Push notification body (max 100 chars) 
            3. SMS content (max 160 chars)
            4. Email subject (max 70 chars)
            5. Email preview (max 200 chars)
            
            Make it engaging and action-oriented.
            """
            
            chat_completion = await self._call_groq_async(prompt)
            response = chat_completion.choices[0].message.content
            
            # Parse AI response into structured format
            # For demo, return mock structured content
            return {
                "push_title": f"🌱 MITRA Update - {notification_type}",
                "push_body": "Your Meri Dharani update is ready!",
                "sms_content": f"MITRA: {notification_type} update ready. Check app for details.",
                "email_subject": f"Meri Dharani - {notification_type} Update",
                "email_preview": "Your environmental impact update from MITRA AI Assistant."
            }
            
        except Exception as e:
            logger.error(f"❌ Notification generation error: {e}")
            return self._get_fallback_notification(user_type, notification_type)
    
    def _get_fallback_notification(self, user_type: str, notification_type: str) -> Dict[str, str]:
        """Fallback notification content"""
        
        return {
            "push_title": f"Meri Dharani - {notification_type}",
            "push_body": "Check your app for updates!",
            "sms_content": f"Meri Dharani: {notification_type} update available.",
            "email_subject": f"Meri Dharani Update - {notification_type}",
            "email_preview": "Your update is ready in the Meri Dharani app."
        }

# Initialize global MITRA service
mitra_ai_service = None

async def get_mitra_service() -> MitraAIService:
    """Get or create MITRA AI service instance"""
    global mitra_ai_service
    
    if not mitra_ai_service:
        import os
        groq_api_key = os.getenv("GROQ_API_KEY")
        
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
            
        mitra_ai_service = MitraAIService(groq_api_key)
        logger.info("✅ MITRA AI Service initialized")
    
    return mitra_ai_service

# Usage Example:
"""
# In your route handlers:

from app.shared.mitra_ai_service import get_mitra_service

async def create_service_request(request_data: dict):
    # Create request...
    
    # Generate AI timeline message
    mitra = await get_mitra_service()
    ai_message = await mitra.generate_timeline_message(
        user_type="citizen",
        step="submitted",
        context={
            "request_id": "WR_2025_001",
            "user_name": "Priya Sharma",
            "location": "Yanamalakuduru"
        }
    )
    
    # Add to timeline...
    timeline_step = {
        "step": "submitted",
        "timestamp": datetime.utcnow(),
        "ai_message": ai_message,
        "details": "Request submitted successfully",
        "mitra_response_time": 0.5
    }
"""