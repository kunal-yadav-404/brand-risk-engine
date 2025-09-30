# test_genai_fixed.py
import os
from genai_explainer import GenAIExplainer

def test_onboarding_explanation():
    """Test onboarding explanation generation"""
    project_id = os.environ['GOOGLE_CLOUD_PROJECT']
    genai = GenAIExplainer(project_id)
    
    # Test with existing merchant
    explanation = genai.generate_onboarding_explanation('TEST_ENH_001')
    print("=== ONBOARDING EXPLANATION ===")
    print(explanation)
    print()

def test_pr_brief():
    """Test PR brief generation"""
    project_id = os.environ['GOOGLE_CLOUD_PROJECT']
    genai = GenAIExplainer(project_id)
    
    # Test with Worldline global (has crisis data)
    brief = genai.generate_pr_brief('WORLDLINE_GLOBAL')
    print("=== PR CRISIS BRIEF ===")
    print(brief)
    print()

if __name__ == '__main__':
    test_onboarding_explanation()
    test_pr_brief()