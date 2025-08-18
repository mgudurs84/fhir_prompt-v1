"""
Script to use the deployed FHIR Testing Agent
Using the correct AgentEngine API methods
"""

import os
import json
import asyncio
import re
from dotenv import load_dotenv
import vertexai
from vertexai import agent_engines

# Load environment variables
load_dotenv()

def clean_json_response(response: str) -> str:
    """Clean markdown formatting from JSON response"""
    if not response:
        return response
    
    # Remove markdown code block formatting
    response = re.sub(r'^```json\s*', '', response, flags=re.MULTILINE)
    response = re.sub(r'^```\s*$', '', response, flags=re.MULTILINE)
    response = response.strip()
    
    # Find JSON content between first { and last }
    start_idx = response.find('{')
    end_idx = response.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return response[start_idx:end_idx + 1]
    
    return response

async def simple_test_deployed_agent():
    """Simple test using the correct AgentEngine API"""
    
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
    LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    STAGING_BUCKET = os.getenv("STAGING_BUCKET")
    
    RESOURCE_NAME = "projects/869395420831/locations/us-central1/reasoningEngines/3620181616871079936"
    
    try:
        vertexai.init(
            project=PROJECT_ID,
            location=LOCATION,
            staging_bucket=STAGING_BUCKET
        )
        
        print("🔗 Getting deployed agent...")
        deployed_agent = agent_engines.get(RESOURCE_NAME)
        
        print("✅ Connected to deployed agent!")
        
        # Create a session
        session = deployed_agent.create_session(user_id="test_user_001")
        print(f"📋 Session created: ID = {session['id']}")
        
        # Simple test prompt
        simple_prompt = """Generate 2 functional test cases for this mapping:
Source_Field: PID.3
Target_FHIR_Resource: Patient
FHIR_Attribute: identifier
Transformation_Rule: Direct mapping
Data_Type: Identifier
Required: Yes

Output JSON format with TestCases array."""

        print("\n🧪 Testing with async_stream_query...")
        
        # Use async_stream_query method
        response_events = []
        async for event in deployed_agent.async_stream_query(
            user_id="test_user_001",
            session_id=session['id'],
            message=simple_prompt
        ):
            response_events.append(event)
            print(f"📨 Event received: {type(event)} - {str(event)[:100]}...")
        
        print(f"✅ Received {len(response_events)} events from deployed agent!")
        
        # Extract the final response
        final_response = None
        for event in response_events:
            if hasattr(event, 'content') and hasattr(event.content, 'parts'):
                for part in event.content.parts:
                    if hasattr(part, 'text'):
                        final_response = part.text
            elif isinstance(event, dict):
                if 'content' in event and 'parts' in event['content']:
                    for part in event['content']['parts']:
                        if 'text' in part:
                            final_response = part['text']
                elif 'text' in event:
                    final_response = event['text']
            elif hasattr(event, 'text'):
                final_response = event.text
            elif isinstance(event, str):
                final_response = event
        
        if final_response:
            print("✅ Response extracted successfully!")
            print(f"📝 Response length: {len(final_response)} chars")
            print(f"📄 Response preview: {final_response[:300]}...")
            
            # Save the response
            with open("simple_deployed_test.txt", "w") as f:
                f.write(final_response)
            
            print("💾 Response saved to 'simple_deployed_test.txt'")
            return final_response
        else:
            print("⚠️ No text response found in events")
            print("🔍 Event details:")
            for i, event in enumerate(response_events[:3]):  # Show first 3 events
                print(f"   Event {i}: {type(event)} - {str(event)}")
            
            # Save all events for debugging
            with open("simple_events_debug.json", "w") as f:
                json.dump([str(event) for event in response_events], f, indent=2)
            
            print("💾 Event debug info saved to 'simple_events_debug.json'")
            return None
            
    except Exception as e:
        print(f"❌ Error in simple test: {str(e)}")
        print(f"🔍 Error type: {type(e).__name__}")
        return None

def test_sync_stream_query():
    """Test using synchronous stream_query"""
    
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
    LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    STAGING_BUCKET = os.getenv("STAGING_BUCKET")
    
    RESOURCE_NAME = "projects/869395420831/locations/us-central1/reasoningEngines/3620181616871079936"
    
    try:
        vertexai.init(
            project=PROJECT_ID,
            location=LOCATION,
            staging_bucket=STAGING_BUCKET
        )
        
        deployed_agent = agent_engines.get(RESOURCE_NAME)
        session = deployed_agent.create_session(user_id="sync_test_user_001")
        
        print("🔄 Testing synchronous stream_query...")
        
        simple_prompt = """Generate 1 test case for PID.3 mapping. Output JSON format."""
        
        # Use synchronous stream_query
        response_stream = deployed_agent.stream_query(
            user_id="sync_test_user_001",
            session_id=session['id'],
            message=simple_prompt
        )
        
        print("✅ Stream query initiated!")
        
        # Collect responses
        responses = []
        for response in response_stream:
            responses.append(response)
            print(f"📨 Sync response: {type(response)} - {str(response)[:100]}...")
        
        print(f"✅ Received {len(responses)} sync responses!")
        
        # Save for debugging
        with open("sync_responses_debug.json", "w") as f:
            json.dump([str(resp) for resp in responses], f, indent=2)
        
        print("💾 Sync responses saved to 'sync_responses_debug.json'")
        
        return responses
        
    except Exception as e:
        print(f"❌ Sync test error: {str(e)}")
        return None

async def use_deployed_agent_full():
    """Full test using the deployed agent"""
    
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
    LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    STAGING_BUCKET = os.getenv("STAGING_BUCKET")
    
    RESOURCE_NAME = "projects/869395420831/locations/us-central1/reasoningEngines/3620181616871079936"
    
    try:
        vertexai.init(
            project=PROJECT_ID,
            location=LOCATION,
            staging_bucket=STAGING_BUCKET
        )
        
        deployed_agent = agent_engines.get(RESOURCE_NAME)
        session = deployed_agent.create_session(user_id="full_test_user_001")
        
        print("🚀 Running full test with deployed agent...")
        
        # Full FHIR prompt
        full_prompt = """Generate functional, regression, and edge test cases for the mapping CSV file that covers every possible attribute.

Current batch number: 001

Please find the ADT to Patient template CSV file below:

Source_Field,Target_FHIR_Resource,FHIR_Attribute,Transformation_Rule,Data_Type,Required,Cardinality,data_type_mapping_details,vocab_mappings
PID.3,Patient,identifier,Direct mapping from patient ID,Identifier,Yes,0..*,Use system http://hospital.org/patient-ids value PID.3.1,N/A
PID.5,Patient,name,Parse HL7 name components,HumanName,No,0..*,family=PID.5.1 given=PID.5.2 prefix=PID.5.5,N/A
PID.7,Patient,birthDate,Convert HL7 date to FHIR date,date,No,0..1,Format YYYY-MM-DD source format YYYYMMDD,N/A
PID.8,Patient,gender,Map HL7 gender codes to FHIR,code,No,0..1,M maps to male F maps to female U maps to unknown,HL7 Table 0001

Generate comprehensive test cases covering:
- Functional test cases (positive and negative)
- Regression test cases  
- Edge test cases

Output format: JSON with TestCases array and StatisticalSummary object.
TestCaseID format: B_001_TC_001_functional_positive
Include TestCaseID, TestDescription, ExpectedOutput, TestSteps, and PassFailCriteria for each test case.

IMPORTANT: Output only pure JSON without any markdown formatting or code blocks."""

        print("🔄 Sending full query to deployed agent...")
        
        # Use async_stream_query for the full prompt
        response_events = []
        async for event in deployed_agent.async_stream_query(
            user_id="full_test_user_001",
            session_id=session['id'],
            message=full_prompt
        ):
            response_events.append(event)
        
        print(f"✅ Received {len(response_events)} events from full query!")
        
        # Extract the final response
        final_response = None
        for event in response_events:
            if hasattr(event, 'content') and hasattr(event.content, 'parts'):
                for part in event.content.parts:
                    if hasattr(part, 'text'):
                        final_response = part.text
            elif isinstance(event, dict):
                if 'content' in event and 'parts' in event['content']:
                    for part in event['content']['parts']:
                        if 'text' in part:
                            final_response = part['text']
                elif 'text' in event:
                    final_response = event['text']
            elif hasattr(event, 'text'):
                final_response = event.text
            elif isinstance(event, str):
                final_response = event
        
        if final_response:
            print("✅ Full response extracted!")
            
            # Clean and process the response
            cleaned_response = clean_json_response(final_response)
            
            print(f"📝 Response length: {len(final_response)} chars")
            print(f"🧹 Cleaned length: {len(cleaned_response)} chars")
            
            # Try to parse JSON
            try:
                result = json.loads(cleaned_response)
                
                print("✅ JSON parsed successfully!")
                
                # Save to file
                with open("deployed_full_results.json", "w") as f:
                    json.dump(result, f, indent=2)
                
                print("📁 Results saved to 'deployed_full_results.json'")
                
                # Show summary
                if "TestCases" in result:
                    print(f"📊 Generated {len(result['TestCases'])} test cases")
                
                if "StatisticalSummary" in result:
                    summary = result["StatisticalSummary"]
                    print(f"📈 Summary: {summary}")
                
                return result
                
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing failed: {e}")
                
                # Save for debugging
                with open("deployed_full_raw.txt", "w") as f:
                    f.write(final_response)
                with open("deployed_full_cleaned.txt", "w") as f:
                    f.write(cleaned_response)
                
                print("💾 Raw and cleaned responses saved for debugging")
                print(f"🔍 Response preview: {final_response[:300]}...")
                
                return final_response
        else:
            print("❌ No response extracted from events")
            return None
            
    except Exception as e:
        print(f"❌ Error in full test: {str(e)}")
        return None

async def main():
    """Main function"""
    
    print("🤖 FHIR Testing Agent - Deployed Version")
    print("=" * 50)
    
    # Check command line arguments
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "simple":
            result = await simple_test_deployed_agent()
            if result:
                print(f"\n✅ Simple test completed successfully!")
            return
            
        elif command == "sync":
            result = test_sync_stream_query()
            if result:
                print(f"\n✅ Sync test completed!")
            return
            
        elif command == "full":
            result = await use_deployed_agent_full()
            if result:
                print(f"\n✅ Full test completed!")
            return
            
        else:
            print(f"❌ Unknown command: {command}")
            print("Available commands: simple, sync, full")
            return
    
    # Default: try both sync and async
    print("🧪 Testing both sync and async methods...")
    
    print("\n1️⃣ Testing synchronous stream_query...")
    sync_result = test_sync_stream_query()
    
    print("\n2️⃣ Testing asynchronous stream_query...")
    async_result = await simple_test_deployed_agent()
    
    if sync_result or async_result:
        print(f"\n✅ At least one method worked!")
        
        user_choice = input("\n🤔 Run full test? (y/n): ").lower()
        if user_choice in ['y', 'yes']:
            print(f"\n🚀 Running full test...")
            full_result = await use_deployed_agent_full()
            
            if full_result:
                print(f"\n🎉 Full test completed successfully!")
        else:
            print("👍 Stopping at simple tests")
    else:
        print(f"\n❌ Both methods failed - check deployment")

if __name__ == "__main__":
    asyncio.run(main())