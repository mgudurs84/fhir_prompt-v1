"""
SDK-based access to FHIR Testing Agent
Using Vertex AI SDK from external projects - Fixed version
"""

import vertexai
from vertexai import agent_engines
import json
import asyncio
import re

class ExternalFHIRAgentAccess:
    """Access FHIR Testing Agent using Vertex AI SDK from external projects"""
    
    def __init__(self, project_id, location="us-central1"):
        """
        Initialize external access
        
        Args:
            project_id: The PROJECT WHERE THE AGENT IS DEPLOYED (vertex-ai-demo-468112)
            location: Agent location (us-central1)
        """
        self.project_id = project_id
        self.location = location
        self.resource_name = "projects/869395420831/locations/us-central1/reasoningEngines/3620181616871079936"
        
        # Initialize Vertex AI with the deployed agent's project
        vertexai.init(
            project=project_id,
            location=location
        )
    
    def get_agent(self):
        """Get the deployed agent instance"""
        try:
            agent = agent_engines.get(self.resource_name)
            print(f"✅ Connected to deployed agent: {self.resource_name}")
            return agent
        except Exception as e:
            print(f"❌ Failed to connect to agent: {e}")
            return None
    
    def clean_json_response(self, response: str) -> str:
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
    
    async def generate_test_cases(self, csv_mapping, batch_number="001", user_id="external_client"):
        """Generate FHIR test cases using the deployed agent"""
        
        agent = self.get_agent()
        if not agent:
            return None
        
        try:
            # Create session
            session = agent.create_session(user_id=user_id)
            print(f"📋 Session created: {session['id']}")
            
            # Prepare prompt
            prompt = f"""Generate functional, regression, and edge test cases for the mapping CSV file that covers every possible attribute.

Current batch number: {batch_number}

Please find the mapping CSV file below:
{csv_mapping}

Generate comprehensive test cases covering:
- Functional test cases (positive and negative)
- Regression test cases  
- Edge test cases

Output format: JSON with TestCases array and StatisticalSummary object.
TestCaseID format: B_{batch_number}_TC_001_functional_positive
Include TestCaseID, TestDescription, ExpectedOutput, TestSteps, and PassFailCriteria for each test case.

IMPORTANT: Output only pure JSON without any markdown formatting or code blocks."""

            print("🚀 Generating test cases...")
            
            # Call the agent
            response_events = []
            async for event in agent.async_stream_query(
                user_id=user_id,
                session_id=session['id'],
                message=prompt
            ):
                response_events.append(event)
            
            # Extract response
            final_response = None
            for event in response_events:
                if isinstance(event, dict) and 'content' in event:
                    if 'parts' in event['content']:
                        for part in event['content']['parts']:
                            if 'text' in part:
                                final_response = part['text']
            
            if final_response:
                print("✅ Test cases generated successfully!")
                return final_response
            else:
                print("❌ No response received")
                return None
                
        except Exception as e:
            print(f"❌ Error generating test cases: {e}")
            return None
    
    def process_and_save_results(self, raw_response, filename="external_project_test_cases.json"):
        """Process raw response and save to file"""
        
        if not raw_response:
            print("❌ No response to process")
            return None
        
        # Clean the response
        cleaned_response = self.clean_json_response(raw_response)
        
        print(f"📝 Raw response length: {len(raw_response)} chars")
        print(f"🧹 Cleaned response length: {len(cleaned_response)} chars")
        
        try:
            json_result = json.loads(cleaned_response)
            
            # Save results
            with open(filename, "w") as f:
                json.dump(json_result, f, indent=2)
            
            print(f"📁 Results saved to '{filename}'")
            
            # Show detailed statistics
            if "TestCases" in json_result:
                test_cases = json_result["TestCases"]
                print(f"📊 Total test cases generated: {len(test_cases)}")
                
                # Count by type and subtype
                type_counts = {}
                subtype_counts = {}
                
                for test_case in test_cases:
                    test_type = test_case.get("TestCaseType", "Unknown")
                    subtype = test_case.get("Subtype", "Unknown")
                    
                    type_counts[test_type] = type_counts.get(test_type, 0) + 1
                    subtype_counts[subtype] = subtype_counts.get(subtype, 0) + 1
                
                print(f"📈 Test types breakdown: {type_counts}")
                print(f"📋 Subtype breakdown: {subtype_counts}")
                
                # Show first few test cases
                print(f"\n🔍 First 3 test cases:")
                for i, test_case in enumerate(test_cases[:3]):
                    print(f"   {i+1}. {test_case.get('TestCaseID', 'N/A')} - {test_case.get('TestCaseType', 'N/A')}/{test_case.get('Subtype', 'N/A')}")
                    print(f"      {test_case.get('TestDescription', 'N/A')[:80]}...")
            
            if "StatisticalSummary" in json_result:
                summary = json_result["StatisticalSummary"]
                print(f"\n📈 StatisticalSummary from agent:")
                for key, value in summary.items():
                    print(f"   {key}: {value}")
            
            return json_result
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing error: {e}")
            print(f"📄 First 300 chars of cleaned response:")
            print(cleaned_response[:300])
            print("...")
            
            # Save raw response for debugging
            raw_filename = filename.replace('.json', '_raw.txt')
            with open(raw_filename, "w") as f:
                f.write(raw_response)
            
            cleaned_filename = filename.replace('.json', '_cleaned.txt')
            with open(cleaned_filename, "w") as f:
                f.write(cleaned_response)
            
            print(f"💾 Raw response saved to '{raw_filename}'")
            print(f"💾 Cleaned response saved to '{cleaned_filename}'")
            
            return {"raw_response": raw_response, "cleaned_response": cleaned_response}

# Usage examples
async def example_usage():
    """Example of how external projects can use the agent"""
    
    # Initialize with the deployed agent's project
    client = ExternalFHIRAgentAccess(
        project_id="vertex-ai-demo-468112",  # The project where agent is deployed
        location="us-central1"
    )
    
    # Sample CSV mapping from external project
    csv_mapping = """Source_Field,Target_FHIR_Resource,FHIR_Attribute,Transformation_Rule,Data_Type,Required,Cardinality,data_type_mapping_details,vocab_mappings
MSH.3,MessageHeader,source,Direct mapping,Reference,Yes,1..1,Use MSH.3 as source application,N/A
PID.3,Patient,identifier,Direct mapping,Identifier,Yes,0..*,Use system http://external-hospital.org/patient-ids,N/A
PID.5,Patient,name,Parse HL7 name components,HumanName,No,0..*,family=PID.5.1 given=PID.5.2,N/A
PID.8,Patient,gender,Map HL7 gender codes,code,No,0..1,M->male F->female U->unknown,HL7 Table 0001
OBX.3,Observation,code,Code mapping,CodeableConcept,Yes,1..1,Map observation codes,LOINC"""
    
    # Generate test cases
    raw_result = await client.generate_test_cases(
        csv_mapping=csv_mapping,
        batch_number="EXT_001",
        user_id="external_project_user"
    )
    
    if raw_result:
        # Process and save results
        processed_result = client.process_and_save_results(
            raw_result, 
            "external_project_test_cases.json"
        )
        
        return processed_result
    else:
        print("❌ Failed to generate test cases")
        return None

async def quick_test():
    """Quick test with simple mapping"""
    
    client = ExternalFHIRAgentAccess(
        project_id="vertex-ai-demo-468112",
        location="us-central1"
    )
    
    simple_csv = """Source_Field,Target_FHIR_Resource,FHIR_Attribute,Transformation_Rule,Data_Type,Required
PID.3,Patient,identifier,Direct mapping,Identifier,Yes
PID.8,Patient,gender,Map gender codes,code,No"""
    
    print("🧪 Running quick test...")
    result = await client.generate_test_cases(
        csv_mapping=simple_csv,
        batch_number="QUICK_001",
        user_id="quick_test_user"
    )
    
    if result:
        processed = client.process_and_save_results(result, "quick_test_results.json")
        return processed
    
    return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        asyncio.run(quick_test())
    else:
        asyncio.run(example_usage())