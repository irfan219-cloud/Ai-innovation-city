# app/citizen/ai_service.py - SIMPLE HACKATHON VERSION

import os
import json
import base64
import asyncio
from datetime import datetime
from typing import Dict, List
from PIL import Image
import io
import cloudinary
import cloudinary.uploader
from groq import Groq

# Configure Cloudinary
cloudinary.config(
    cloud_name="dsgnz3ekm",
    api_key="564283999996143", 
    api_secret="nwZjI34gSGiRbngknWdv4nYtcuc"
)

class SimpleMithraAI:
    def __init__(self):
        self.groq_client = Groq(api_key="GROQ_API_KEY")
        print("✅ MITRA AI Ready for Hackathon!")

    async def complete_analysis_pipeline(self, request_data: Dict, user_language: str = "en") -> Dict:
        """AI Pipeline: Image Analysis → Validation → Content Generation"""
        
        try:
            print("\n" + "="*50)
            print("🤖 MITRA AI: Processing waste management request")
            print("="*50)
            print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📍 Location: {request_data.get('location', {}).get('address', 'Unknown')}")
            print(f"📝 Description: {request_data.get('description', 'No description')[:50]}...")
            
            # STEP 2: AI Image Analysis FIRST (before uploading)
            print("\n🔍 Analyzing images with computer vision...")
            image_analysis = {}
            if request_data.get("images"):
                image_analysis = await self._analyze_image_simple(request_data["images"][0])
                waste_type = image_analysis.get('waste_type', 'unknown')
                confidence = image_analysis.get('confidence', 0.0)
                print(f"✅ Detected: {waste_type} (confidence: {confidence:.2f})")
                print(f"📊 Analysis: {image_analysis.get('description', 'No description')[:80]}...")
            else:
                print("❌ No images to analyze")
            
            # STEP 1: Upload images to Cloudinary (after analysis)
            print("\n📸 Uploading images to cloud storage...")
            cloudinary_urls = []
            if request_data.get("images"):
                cloudinary_urls = await self._upload_to_cloudinary(request_data["images"])
                print(f"✅ {len(cloudinary_urls)} images uploaded successfully")
            else:
                print("⚠️  No images provided")
            
            # STEP 3: Request Validation
            print("\n🛡️  Validating request authenticity...")
            validation = await self._validate_request_simple(
                user_description=request_data.get("description", ""),
                ai_analysis=image_analysis
            )
            
            if not validation.get("is_valid", False):
                print(f"❌ Validation failed: {validation.get('reason', 'Invalid request')}")
                return {
                    "status": "rejected",
                    "message": validation.get("reason", "Request validation failed"),
                    "cloudinary_urls": cloudinary_urls
                }
            
            print(f"✅ Request validated (score: {validation.get('score', 0)}/10)")
            
            # STEP 4: Generate Enhanced Content
            print("\n🎨 Generating enhanced content...")
            beautiful_content = await self._beautify_content_simple(
                user_description=request_data.get("description", ""),
                ai_analysis=image_analysis,
                location=request_data.get("location", {})
            )
            
            points = beautiful_content.get('eco_points', 0)
            impact = beautiful_content.get('environmental_impact', {})
            print(f"✅ Content generated: {points} eco points awarded")
            print(f"🌱 Environmental impact: {impact.get('co2_saved', 0)}kg CO2 saved")
            
            # STEP 5: Final Assembly
            final_result = {
                "status": "success",
                "cloudinary_urls": cloudinary_urls,
                "ai_analysis": image_analysis,
                "validation": validation,
                "beautiful_content": beautiful_content,
                "processing_time": 3.0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            print("\n" + "="*50)
            print("🎉 AI Pipeline completed successfully!")
            print("="*50)
            
            return final_result
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "cloudinary_urls": cloudinary_urls if 'cloudinary_urls' in locals() else []
            }

    async def _upload_to_cloudinary(self, images: List[Dict]) -> List[str]:
        """Upload images to Cloudinary"""
        urls = []
        
        for idx, img_data in enumerate(images):
            try:
                image_path = img_data.get("file_path")
                if not os.path.exists(image_path):
                    print(f"⚠️  Image {idx+1} not found at path")
                    continue
                
                # Upload to Cloudinary
                result = cloudinary.uploader.upload(
                    image_path,
                    folder="meri_dharani",
                    public_id=f"waste_{int(datetime.utcnow().timestamp())}_{idx}"
                )
                
                urls.append(result.get("secure_url"))
                print(f"  📤 Image {idx+1}: Upload complete")
                
                # Delete local file
                try:
                    os.remove(image_path)
                except:
                    pass
                    
            except Exception as e:
                print(f"  ❌ Upload failed for image {idx+1}: {str(e)[:50]}...")
                
        return urls

    async def _analyze_image_simple(self, image_data: Dict) -> Dict:
        """AI image analysis using Groq Vision"""
        try:
            image_path = image_data.get("file_path")
            
            # Convert to base64
            with Image.open(image_path) as img:
                if img.size[0] > 1024:
                    img.thumbnail((1024, 1024))
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=80)
                img_b64 = base64.b64encode(buffered.getvalue()).decode()
            
            print("  🧠 Sending image to AI model...")
            
            # Call Groq Vision API
            response = self.groq_client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this image for waste management. What type of waste do you see? Is it recyclable? Describe in 2-3 sentences. Also estimate if this is: plastic, organic, metal, glass, mixed, or other waste."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                        }
                    ]
                }],
                temperature=0.3,
                max_tokens=200
            )
            
            ai_description = response.choices[0].message.content
            
            # Simple waste type extraction
            waste_type = "mixed"
            if "plastic" in ai_description.lower():
                waste_type = "plastic"
            elif "organic" in ai_description.lower() or "food" in ai_description.lower():
                waste_type = "organic" 
            elif "metal" in ai_description.lower():
                waste_type = "metal"
            elif "glass" in ai_description.lower():
                waste_type = "glass"
            
            result = {
                "description": ai_description,
                "waste_type": waste_type,
                "confidence": 0.85,
                "recyclable": "recycl" in ai_description.lower(),
                "ai_model": "llama-4-scout-17b"
            }
            
            print(f"  🎯 AI detected: {waste_type} waste")
            return result
            
        except Exception as e:
            print(f"  ❌ AI analysis failed: {str(e)[:50]}...")
            return {
                "description": "Could not analyze image",
                "waste_type": "unknown",
                "confidence": 0.0,
                "error": str(e)
            }

    async def _validate_request_simple(self, user_description: str, ai_analysis: Dict) -> Dict:
        """Validate if request is genuine waste report"""
        try:
            print("  🔍 Cross-checking user description with AI analysis...")
            
            # Basic validation rules
            if len(user_description.strip()) < 5:
                return {"is_valid": False, "reason": "Description too short", "score": 2}
            
            # Check for test/fake keywords
            fake_keywords = ["test", "testing", "demo", "sample", "asdf", "123", "fake"]
            if any(word in user_description.lower() for word in fake_keywords):
                return {"is_valid": False, "reason": "Appears to be a test submission", "score": 1}
            
            # AI validation using Groq
            validation_prompt = f"""
            User description: "{user_description}"
            AI image analysis: "{ai_analysis.get('description', '')}"
            
            Is this a genuine waste management request? Consider:
            1. Does description match the image analysis?
            2. Is it a real environmental concern?
            3. Is the user serious about waste cleanup?
            
            Respond with: VALID or INVALID and give a score 1-10 and brief reason.
            """
            
            response = self.groq_client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{"role": "user", "content": validation_prompt}],
                temperature=0.2,
                max_tokens=100
            )
            
            validation_result = response.choices[0].message.content
            
            is_valid = "VALID" in validation_result.upper() and "INVALID" not in validation_result.upper()
            
            # Extract score
            score = 7  # default
            import re
            score_match = re.search(r'(\d+)', validation_result)
            if score_match:
                score = int(score_match.group(1))
            
            result = {
                "is_valid": is_valid,
                "score": score,
                "reason": validation_result,
                "ai_validation": True
            }
            
            print(f"  ✅ Validation: {'PASS' if is_valid else 'FAIL'} (score: {score}/10)")
            return result
            
        except Exception as e:
            print(f"  ⚠️  Validation error, defaulting to valid: {str(e)[:30]}...")
            return {"is_valid": True, "score": 6, "reason": "Validation service unavailable"}

    async def _beautify_content_simple(self, user_description: str, ai_analysis: Dict, location: Dict) -> Dict:
        """AI generates dynamic JSON fields including cleaned description"""
        try:
            print("  ✨ Creating dynamic JSON insights...")
            
            waste_type = ai_analysis.get('waste_type', 'mixed')
            area = location.get('address', 'unknown')
            
            # Let AI decide what fields to include
            prompt = f"""
            Analyze this waste situation and create JSON with relevant fields:

            User input: "{user_description}"
            Detected waste: {waste_type}
            Location: {area}
            AI analysis: {ai_analysis.get('description', '')}

            Based on this specific situation, create JSON with fields that make sense.
            Always include a cleaned_description that transforms the user's input into professional text.

            You might include fields like:
            - cleaned_description (professional version of user input)
            - title, worker_type, estimated_cost, priority
            - urgency_level, safety_requirements, recycling_value
            - special_handling, time_estimate, equipment_needed

            But decide what's actually relevant for THIS specific waste case.

            Respond with ONLY valid JSON:
            """
            
            response = self.groq_client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{
                    "role": "system",
                    "content": "Respond with valid JSON only. Include cleaned_description and other relevant fields based on the waste situation. No explanations."
                }, {
                    "role": "user", 
                    "content": prompt
                }],
                temperature=0.5,
                max_tokens=400
            )
            
            # Parse the dynamic JSON response
            json_response = response.choices[0].message.content.strip()
            return json.loads(json_response)
            
        except Exception as e:
            print(f"  ⚠️  Dynamic fallback: {str(e)[:20]}...")
            return {
                "cleaned_description": f"Waste cleanup required for {waste_type} materials in {area}. Professional assessment and removal needed.",
                "title": f"{waste_type.title()} Waste Management",
                "worker_type": "ngo_specialist" if waste_type in ["e-waste", "cloth"] else "municipal_worker",
                "estimated_cost": "₹300-700",
                "priority": "medium",
                "category": waste_type
            }

async def store_request_with_mithra_insights(db, user_id: str, request_data: Dict, mithra_insights: Dict) -> str:
    """Store the request in 'requests' collection"""
    try:
        print(f"\n💾 Storing request in database...")
        print(f"  📊 Status: {mithra_insights.get('status', 'unknown')}")
        print("SSS")
        print(f"  🗄️  Database type: {type(db)}")
        
        if db is None:
            print("  ⚠️  No database connection - using demo mode")
            return f"DEMO_{request_data.get('request_id', 'unknown')}"
        
        # Create database document
        request_doc = {
            "request_id": request_data.get("request_id"),
            "user_id": user_id,
            "status": "submitted", 
            "created_at": datetime.utcnow(),
            "user_description": request_data.get("description", ""),
            "location": request_data.get("location", {}),
            "ai_analysis": mithra_insights.get("ai_analysis", {}),
            "validation": mithra_insights.get("validation", {}),
            "content": mithra_insights.get("beautiful_content", {}),
            "cloudinary_urls": mithra_insights.get("cloudinary_urls", []),
            "processing_complete": True
        }
        
        # Store in REQUESTS collection specifically
        try:
            if hasattr(db, 'database') and db.database is not None:
                requests_collection = db.database.requests  # ← REQUESTS COLLECTION
                result = await requests_collection.insert_one(request_doc)
                stored_id = str(result.inserted_id)
                print(f"  ✅ Stored in REQUESTS collection: {stored_id}")
                return stored_id
            else:
                print(f"  ❌ No database.requests collection found")
                return f"ERROR_{request_data.get('request_id', 'unknown')}"
                
        except Exception as db_error:
            print(f"  ❌ Database error: {str(db_error)}")
            return f"ERROR_{request_data.get('request_id', 'unknown')}"
        
    except Exception as e:
        print(f"  ❌ Storage failed: {str(e)}")
        return f"ERROR_{request_data.get('request_id', 'unknown')}"