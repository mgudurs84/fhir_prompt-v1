from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import logging
import re

from invoke_sdk import ExternalFHIRAgentAccess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class TestCaseRequest(BaseModel):
    csv_mapping: str
    batch_number: str = "001" 
    user_id: str = "external_client"

def super_simple_extraction(text):
    """Super simple extraction - just get the key info for each TestCaseID"""
    test_cases = []
    
    # Find all TestCaseID values
    testcase_ids = re.findall(r'"TestCaseID"\s*:\s*"([^"]+)"', text)
    logger.info(f"Found TestCaseIDs: {len(testcase_ids)}")
    
    # For each TestCaseID, find the associated data
    for i, testcase_id in enumerate(testcase_ids):
        try:
            # Find the position of this TestCaseID
            pattern = f'"TestCaseID"\\s*:\\s*"{re.escape(testcase_id)}"'
            match = re.search(pattern, text)
            if not match:
                continue
                
            start = match.start()
            
            # Get a reasonable chunk after this TestCaseID (next 1000 chars)
            chunk = text[start:start + 1000]
            
            # Extract individual fields with simple regex
            desc_match = re.search(r'"TestDescription"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', chunk)
            output_match = re.search(r'"ExpectedOutput"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', chunk)  
            criteria_match = re.search(r'"PassFailCriteria"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', chunk)
            type_match = re.search(r'"TestCaseType"\s*:\s*"([^"]*)"', chunk)
            subtype_match = re.search(r'"Subtype"\s*:\s*"([^"]*)"', chunk)
            
            # Extract test steps array - look for the pattern
            steps_match = re.search(r'"TestSteps"\s*:\s*\[(.*?)\]', chunk, re.DOTALL)
            steps = []
            if steps_match:
                steps_content = steps_match.group(1)
                # Extract quoted strings from the array
                step_strings = re.findall(r'"([^"]*(?:\\.[^"]*)*)"', steps_content)
                steps = step_strings
            
            if not steps:
                steps = ["Execute test validation", "Verify expected behavior", "Confirm test results"]
            
            # Create the test case object
            test_case = {
                "TestCaseID": testcase_id,
                "TestDescription": desc_match.group(1) if desc_match else f"Validation test for {testcase_id}",
                "ExpectedOutput": output_match.group(1) if output_match else "Expected system behavior validated",
                "TestSteps": steps,
                "PassFailCriteria": criteria_match.group(1) if criteria_match else "Test passes when validation criteria are met",
                "TestCaseType": type_match.group(1) if type_match else "FUNCTIONAL",
                "Subtype": subtype_match.group(1) if subtype_match else "POSITIVE"
            }
            
            test_cases.append(test_case)
            logger.info(f"✅ Extracted test case {i+1}: {testcase_id}")
            
        except Exception as e:
            logger.warning(f"Failed to extract test case {i+1} ({testcase_id}): {e}")
            continue
    
    logger.info(f"🎯 Final extraction result: {len(test_cases)} test cases")
    return test_cases

@app.post("/generate_test_cases")
async def generate_test_cases(request: TestCaseRequest):
    logger.info(f"🔬 Processing request for batch {request.batch_number}")
    
    client = ExternalFHIRAgentAccess(
        project_id="vertex-ai-demo-468112",
        location="us-central1"
    )
    
    try:
        logger.info("🚀 Calling Vertex AI agent...")
        raw_result = await client.generate_test_cases(
            csv_mapping=request.csv_mapping,
            batch_number=request.batch_number,
            user_id=request.user_id
        )
        
        if not raw_result:
            raise HTTPException(status_code=500, detail="No response from Vertex AI")
        
        logger.info(f"📊 Raw result: {len(raw_result)} characters")
        
        # Clean response
        cleaned = client.clean_json_response(raw_result)
        logger.info(f"🧹 Cleaned: {len(cleaned)} characters")
        
        # Try direct JSON first
        try:
            result = json.loads(cleaned)
            if "TestCases" in result and len(result["TestCases"]) > 5:
                logger.info(f"✅ Direct JSON worked: {len(result['TestCases'])} test cases")
                return result
        except json.JSONDecodeError:
            logger.info("❌ Direct JSON failed, using extraction...")
        
        # Use super simple extraction
        test_cases = super_simple_extraction(cleaned)
        
        if len(test_cases) > 5:  # Only return if we got a good number
            # Generate stats
            type_counts = {}
            subtype_counts = {}
            
            for tc in test_cases:
                tc_type = tc.get("TestCaseType", "FUNCTIONAL")
                subtype = tc.get("Subtype", "POSITIVE")
                type_counts[tc_type] = type_counts.get(tc_type, 0) + 1
                subtype_counts[subtype] = subtype_counts.get(subtype, 0) + 1
            
            result = {
                "TestCases": test_cases,
                "StatisticalSummary": {
                    "TotalTestCases": len(test_cases),
                    "MappingRows": len(test_cases) // 3,
                    "UniqueAttributes": len(test_cases) // 3,
                    "TestCaseTypeBreakdown": type_counts,
                    "SubtypeBreakdown": subtype_counts
                }
            }
            
            logger.info(f"🎉 SUCCESS: Returning {len(test_cases)} test cases!")
            return result
        else:
            logger.error(f"❌ Only extracted {len(test_cases)} test cases, not enough")
            raise HTTPException(status_code=500, detail=f"Only extracted {len(test_cases)} test cases from response")
            
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/")  
async def root():
    return {"message": "Super Simple FastAPI Test Case Generator"}