# dependency_agent.py (For CycleGAN)

import os
import sys
import google.generativeai as genai

# Import the universal engine
from agent_logic import DependencyAgent

AGENT_CONFIG = {
    "PROJECT_NAME": "cyclegan",
    
    # CycleGAN is usually run as scripts, not installed as a package.
    "IS_INSTALLABLE_PACKAGE": False, 

    "REQUIREMENTS_FILE": "requirements.txt",
    "METRICS_OUTPUT_FILE": "metrics_output.txt",
    "PRIMARY_REQUIREMENTS_FILE": "primary_requirements.txt",

    "VALIDATION_CONFIG": {
        "type": "script",
        "smoke_test_script": "validation_cyclegan.py",
        # We run in the root so 'from models import networks' works
        "project_dir": "." 
    },
    
    "MAX_RUN_PASSES": 3,
}

if __name__ == "__main__":
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        sys.exit("CRITICAL ERROR: GEMINI_API_KEY environment variable not set.")
    
    genai.configure(api_key=GEMINI_API_KEY)
    llm_client = genai.GenerativeModel('gemini-2.5-flash')

    agent = DependencyAgent(config=AGENT_CONFIG, llm_client=llm_client)
    agent.run()