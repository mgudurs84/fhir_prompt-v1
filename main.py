"""
Main script to run the FHIR Testing Agent
With deployment functionality to Google Cloud Platform
Using service account impersonation for cross-project access
"""

import os
import json
import asyncio
import re
import sys
from dotenv import load_dotenv
from vertexai.preview.reasoning_engines import AdkApp
from vertexai import agent_engines
from agent import root_agent
import vertexai
import google.auth
from google.auth import impersonated_credentials

# Load environment variables
load_dotenv()

def setup_impersonated_credentials():
    """Setup impersonated credentials for cross-project access"""
    try:
        # Target scopes for Vertex AI and Cloud Storage
        target_scopes = [
            'https://www.googleapis.com/auth/cloud-platform',
            'https://www.googleapis.com/auth/storage-full-control',
            'https://www.googleapis.com/auth/aiplatform'
        ]
        
        # Get default credentials
        source_creds, project_id = google.auth.default()
        
        # Service account to impersonate for compute operations
        target_service_account = os.getenv("TARGET_SERVICE_ACCOUNT", 
            "vertex-agent-service@anbc-dev-cdr-de.iam.gserviceaccount.com")
        
        # Create impersonated credentials
        impersonated_creds = impersonated_credentials.Credentials(
            source_credentials=source_creds,
            target_principal=target_service_account,
            target_scopes=target_scopes
        )
        
        print(f"✅ Impersonated credentials setup successful")
        print(f"🎭 Target service account: {target_service_account}")
        
        return impersonated_creds
        
    except Exception as e:
        print(f"❌ Failed to setup impersonated credentials: {str(e)}")
        print("💡 Falling back to default credentials")
        return None

def get_project_config():
    """Get project configuration for storage and compute"""
    
    # Check if we're using cross-project deployment (anbc-dev setup)
    use_cross_project = os.getenv("USE_CROSS_PROJECT_DEPLOYMENT", "false").lower() == "true"
    
    if use_cross_project:
        # Cross-project setup: anbc-dev for storage, anbc-dev-cdr-de for compute
        config = {
            "storage_project": os.getenv("STORAGE_PROJECT", "anbc-dev"),
            "staging_bucket": os.getenv("CROSS_PROJECT_STAGING_BUCKET", "gs://anbc-dev-vertex-staging"),
            "compute_project": os.getenv("COMPUTE_PROJECT", "anbc-dev-cdr-de"),
            "location": os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            "target_service_account": os.getenv("TARGET_SERVICE_ACCOUNT", 
                "vertex-agent-service@anbc-dev-cdr-de.iam.gserviceaccount.com"),
            "use_impersonation": True
        }
    else:
        # Single project setup using existing .env configuration
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT not set in .env file")
            
        config = {
            "storage_project": project_id,
            "staging_bucket": os.getenv("STAGING_BUCKET"),
            "compute_project": project_id,
            "location": os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            "target_service_account": None,
            "use_impersonation": False
        }
        
        if not config["staging_bucket"]:
            raise ValueError("STAGING_BUCKET not set in .env file")
    
    print("🔧 Project Configuration:")
    print(f"   Mode: {'Cross-Project' if use_cross_project else 'Single Project'}")
    print(f"   Storage Project: {config['storage_project']}")
    print(f"   Staging Bucket: {config['staging_bucket']}")
    print(f"   Compute Project: {config['compute_project']}")
    print(f"   Location: {config['location']}")
    if config.get("target_service_account"):
        print(f"   Service Account: {config['target_service_account']}")
    
    return config

def initialize_vertex_ai(config, credentials=None):
    """Initialize Vertex AI with proper project and credentials"""
    try:
        # Initialize with compute project and staging bucket
        init_params = {
            "project": config["compute_project"],
            "location": config["location"],
            "staging_bucket": config["staging_bucket"]
        }
        
        # Add credentials if using impersonation
        if credentials:
            init_params["credentials"] = credentials
        
        vertexai.init(**init_params)
        
        print(f"✅ Vertex AI initialized successfully!")
        print(f"   Compute Project: {config['compute_project']}")
        print(f"   Staging Bucket: {config['staging_bucket']}")
        print(f"   Using Impersonation: {config.get('use_impersonation', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Vertex AI initialization failed: {str(e)}")
        return False

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

async def test_local_agent():
    """Test the agent locally before deployment"""
    
    print("🧪 Testing agent locally...")
    
    # Setup configuration
    config = get_project_config()
    
    # Setup credentials based on configuration
    credentials = None
    if config.get("use_impersonation"):
        credentials = setup_impersonated_credentials()
    
    # Initialize Vertex AI
    if not initialize_vertex_ai(config, credentials):
        return None
    
    try:
        # Create ADK app
        app = AdkApp(agent=root_agent)
        
        print(f"🤖 Agent: {root_agent.name}")
        
        # Simple test prompt
        test_prompt = """Generate 2 functional test cases for this mapping:
Source_Field,Target_FHIR_Resource,FHIR_Attribute,Transformation_Rule,Data_Type,Required
PID.3,Patient,identifier,Direct mapping,Identifier,Yes

Output format: JSON with TestCases array and StatisticalSummary object.
TestCaseID format: B_001_TC_001_functional_positive"""

        print("\n🔬 Running test query...")
        
        # Query the agent
        response_events = []
        async for event in app.async_stream_query(
            user_id="test_user",
            message=test_prompt
        ):
            response_events.append(event)
        
        # Extract response
        final_response = None
        for event in response_events:
            if event.get('content') and event['content'].get('parts'):
                for part in event['content']['parts']:
                    if 'text' in part:
                        final_response = part['text']
        
        if final_response:
            print("✅ Local test successful!")
            print(f"📄 Response length: {len(final_response)} chars")
            
            # Try to parse JSON
            cleaned_response = clean_json_response(final_response)
            try:
                result = json.loads(cleaned_response)
                print("✅ JSON parsing successful!")
                return app
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing failed: {e}")
                print("⚠️ Will still proceed with deployment")
                return app
        else:
            print("❌ Local test failed - no response")
            return None
            
    except Exception as e:
        print(f"❌ Local test error: {str(e)}")
        return None

async def deploy_to_agent_engine(app):
    """Deploy the agent to Vertex AI Agent Engine"""
    
    try:
        config = get_project_config()
        
        print("\n🚀 Deploying to Vertex AI Agent Engine...")
        if config.get("use_impersonation"):
            print("📍 Deploying to: anbc-dev-cdr-de")
            print("💾 Using staging bucket from: anbc-dev")
            print("🎭 Using service account impersonation")
        else:
            print(f"📍 Deploying to: {config['compute_project']}")
            print(f"💾 Using staging bucket: {config['staging_bucket']}")
        print("⏱️ This may take 5-10 minutes...")
        
        # Deploy to Agent Engine
        remote_agent = agent_engines.create(
            agent_engine=app,
            requirements=[
                "google-adk>=1.0.0",
                "google-cloud-aiplatform[adk,agent_engines]>=1.108.0",
                "pyyaml>=6.0",
                "python-dotenv>=1.0.0",
                "pydantic>=2.11.7",
                "cloudpickle>=3.0.0"
            ]
        )
        
        print(f"✅ Agent deployed successfully!")
        print(f"📄 Resource name: {remote_agent.resource_name}")
        print(f"🔗 Resource ID: {remote_agent.resource_name.split('/')[-1]}")
        
        # Save deployment info
        deployment_info = {
            "resource_name": remote_agent.resource_name,
            "compute_project": config["compute_project"],
            "storage_project": config["storage_project"],
            "location": config["location"],
            "staging_bucket": config["staging_bucket"],
            "use_impersonation": config.get("use_impersonation", False),
            "deployment_time": str(asyncio.get_event_loop().time()),
            "agent_name": root_agent.name
        }
        
        if config.get("target_service_account"):
            deployment_info["target_service_account"] = config["target_service_account"]
        
        with open("deployment_info.json", "w") as f:
            json.dump(deployment_info, f, indent=2)
        
        print("💾 Deployment info saved to 'deployment_info.json'")
        
        return remote_agent
        
    except Exception as e:
        print(f"❌ Deployment failed: {str(e)}")
        print("\nPossible issues:")
        if config.get("use_impersonation"):
            print("1. Agent Engine API not enabled in anbc-dev-cdr-de")
            print("2. Insufficient permissions for service account impersonation")
            print("3. Cross-project staging bucket access issues")
            print("4. Resource quota limits in anbc-dev-cdr-de")
            print("5. Service account vertex-agent-service@anbc-dev-cdr-de.iam.gserviceaccount.com missing permissions")
        else:
            print("1. Agent Engine API not enabled")
            print("2. Insufficient permissions")
            print("3. Staging bucket access issues")
            print("4. Resource quota limits")
        return None

async def test_deployed_agent(remote_agent):
    """Test the deployed agent"""
    
    try:
        print("\n🧪 Testing deployed agent...")
        
        # Create a session
        session = remote_agent.create_session(user_id="test_deployment")
        print(f"📋 Session created: {session.id}")
        
        # Test query
        test_prompt = """Generate 1 functional test case for PID.3 to Patient.identifier mapping.
Output JSON format with TestCases array."""
        
        print("🔬 Running deployment test query...")
        
        # Query the deployed agent
        response_events = []
        async for event in remote_agent.async_stream_query(
            user_id="test_deployment",
            session_id=session.id,
            message=test_prompt
        ):
            response_events.append(event)
        
        # Extract response
        final_response = None
        for event in response_events:
            if event.get('content') and event['content'].get('parts'):
                for part in event['content']['parts']:
                    if 'text' in part:
                        final_response = part['text']
        
        if final_response:
            print("✅ Deployed agent test successful!")
            print(f"📄 Response preview: {final_response[:200]}...")
            
            # Save test result
            with open("deployment_test_result.txt", "w") as f:
                f.write(final_response)
            
            print("💾 Deployment test result saved")
            return True
        else:
            print("❌ Deployed agent test failed")
            return False
            
    except Exception as e:
        print(f"❌ Deployment test error: {str(e)}")
        return False

async def run_full_example_locally():
    """Run the full example locally (original functionality)"""
    
    print("🏠 Running full example locally...")
    
    # Setup configuration
    config = get_project_config()
    
    # Setup credentials based on configuration
    credentials = None
    if config.get("use_impersonation"):
        credentials = setup_impersonated_credentials()
    
    # Initialize Vertex AI
    if not initialize_vertex_ai(config, credentials):
        return
    
    try:
        # Create ADK app
        app = AdkApp(agent=root_agent)
        
        print(f"🎯 FHIR Testing Agent initialized successfully!")
        print(f"🤖 Agent name: {root_agent.name}")
        
        # Full example prompt
        user_prompt = """Generate functional, regression, and edge test cases for the mapping CSV file that covers every possible attribute.

Current batch number: 001

Please find the ADT to Patient template CSV file below:

Source_Field,Target_FHIR_Resource,FHIR_Attribute,Transformation_Rule,Data_Type,Required,Cardinality,data_type_mapping_details,vocab_mappings
PID.3,Patient,identifier,Direct mapping from patient ID,Identifier,Yes,0..*,Use system http://hospital.org/patient-ids value PID.3.1,N/A
PID.5,Patient,name,Parse HL7 name components,HumanName,No,0..*,family=PID.5.1 given=PID.5.2 prefix=PID.5.5,N/A
PID.7,Patient,birthDate,Convert HL7 date to FHIR date,date,No,0..1,Format YYYY-MM-DD source format YYYYMMDD,N/A
PID.8,Patient,gender,Map HL7 gender codes to FHIR,code,No,0..1,M maps to male F maps to female U maps to unknown,HL7 Table 0001
PID.11,Patient,address,Parse HL7 address components,Address,No,0..*,line=PID.11.1 city=PID.11.3 state=PID.11.4 postalCode=PID.11.5,N/A

Generate comprehensive test cases covering:
- Functional test cases (positive and negative)
- Regression test cases  
- Edge test cases

Output format: JSON with TestCases array and StatisticalSummary object.
TestCaseID format: B_001_TC_001_functional_positive
Include TestCaseID, TestDescription, ExpectedOutput, TestSteps, and PassFailCriteria for each test case.

IMPORTANT: Output only pure JSON without any markdown formatting or code blocks."""

        print("\n⚙️ Generating test cases...")
        print("⏱️ This may take a few moments...")
        
        # Query the agent
        response_events = []
        async for event in app.async_stream_query(
            user_id="fhir_tester",
            message=user_prompt
        ):
            response_events.append(event)
        
        # Extract response
        final_response = None
        for event in response_events:
            if event.get('content') and event['content'].get('parts'):
                for part in event['content']['parts']:
                    if 'text' in part:
                        final_response = part['text']
        
        if final_response:
            print("✅ Response received!")
            
            # Clean the response
            cleaned_response = clean_json_response(final_response)
            
            print(f"📄 Response length: {len(final_response)} chars")
            print(f"🧹 Cleaned length: {len(cleaned_response)} chars")
            
            # Try to parse as JSON
            try:
                result = json.loads(cleaned_response)
                
                print("✅ JSON parsed successfully!")
                
                # Save to file
                with open("generated_test_cases.json", "w") as f:
                    json.dump(result, f, indent=2)
                
                print("📄 Results saved to 'generated_test_cases.json'")
                
                # Show summary
                if "TestCases" in result:
                    print(f"📊 Generated {len(result['TestCases'])} test cases")
                
                if "StatisticalSummary" in result:
                    summary = result["StatisticalSummary"]
                    print(f"📈 Summary: {summary}")
                
                # Show first test case
                if "TestCases" in result and result["TestCases"]:
                    first_test = result["TestCases"][0]
                    print(f"📄 First test case: {first_test.get('TestCaseID', 'N/A')}")
                    print(f"📝 Description: {first_test.get('TestDescription', 'N/A')[:100]}...")
                
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing failed: {e}")
                
                # Save both responses for debugging
                with open("raw_response.txt", "w") as f:
                    f.write(final_response)
                with open("cleaned_response.txt", "w") as f:
                    f.write(cleaned_response)
                
                print("💾 Raw and cleaned responses saved for debugging")
        else:
            print("❌ No response generated")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

async def main():
    """Main function with deployment options"""
    
    print("🚀 FHIR Testing Agent - Cross-Project Deployment Ready")
    print("=" * 60)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "deploy":
            print("🚀 DEPLOYMENT MODE")
            
            # Check configuration mode
            config = get_project_config()
            if config.get("use_impersonation"):
                print("📍 Storage: anbc-dev (staging bucket)")
                print("🖥️  Compute: anbc-dev-cdr-de (agent engine)")
                print("🎭 Using service account impersonation")
            else:
                print(f"📍 Project: {config['compute_project']}")
                print(f"🖥️  Using standard authentication")
            
            # Test locally first
            app = await test_local_agent()
            if not app:
                print("❌ Local test failed. Fix issues before deployment.")
                return
            
            # Deploy to Agent Engine
            remote_agent = await deploy_to_agent_engine(app)
            if remote_agent:
                # Test deployed agent
                await test_deployed_agent(remote_agent)
                
                print("\n🎉 DEPLOYMENT COMPLETE!")
                print("📋 Next steps:")
                print("1. Check deployment_info.json for resource details")
                if config.get("use_impersonation"):
                    print("2. Access your agent via the Vertex AI console in anbc-dev-cdr-de")
                else:
                    print(f"2. Access your agent via the Vertex AI console in {config['compute_project']}")
                print("3. Use the resource name for API calls")
                
            return
            
        elif command == "test":
            print("🧪 TEST MODE")
            app = await test_local_agent()
            return
            
        elif command == "local":
            print("🏠 LOCAL MODE")
            await run_full_example_locally()
            return
            
        else:
            print(f"❌ Unknown command: {command}")
            print("Available commands: deploy, test, local")
            return
    
    # Default: show options
    print("Choose an option:")
    print("1. python main.py local     - Run full example locally")
    print("2. python main.py test      - Test agent locally")  
    print("3. python main.py deploy    - Deploy to GCP Agent Engine")
    print("")
    print("💡 Recommendation: Start with 'test' then 'deploy'")
    print("")
    print("🔧 Configuration Mode:")
    
    # Show current configuration
    try:
        config = get_project_config()
        if config.get("use_impersonation"):
            print("   Cross-Project Deployment: Enabled")
            print("   Storage Project: anbc-dev")
            print("   Compute Project: anbc-dev-cdr-de")
            print("   Service Account Impersonation: Enabled")
            print("")
            print("💡 To use single-project mode, set USE_CROSS_PROJECT_DEPLOYMENT=false in .env")
        else:
            print("   Single Project Deployment: Enabled")
            print(f"   Project: {config['compute_project']}")
            print("   Service Account Impersonation: Disabled")
            print("")
            print("💡 To use cross-project mode, set USE_CROSS_PROJECT_DEPLOYMENT=true in .env")
    except Exception as e:
        print(f"   Configuration Error: {e}")
        print("   Please check your .env file")

if __name__ == "__main__":
    asyncio.run(main())
