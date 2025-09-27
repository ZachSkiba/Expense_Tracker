# app/services/auth/security_questions.py - Security Questions Service

class SecurityQuestionsService:
    """Handle predefined security questions for password recovery"""
    
    # Predefined security questions
    SECURITY_QUESTIONS = [
        "What was your childhood dream job?",
        "What were you doing on New Year's Eve 2000?",
        "What was the name of your first pet?",
        "What city were you born in?",
        "What is your mother's maiden name?",
        "What was the name of your elementary school?",
        "What is the name of the street you grew up on?",
        "What is your favorite movie?",
        "What is your father's middle name?",
        "What was the name of your favorite teacher?",
        "What is the name of the first book you read?",
        "What was your favorite food as a child?"
    ]
    
    @staticmethod
    def get_questions():
        """Get list of all available security questions"""
        return SecurityQuestionsService.SECURITY_QUESTIONS.copy()
    
    @staticmethod
    def validate_question(question):
        """Validate that the question is from our predefined list"""
        return question in SecurityQuestionsService.SECURITY_QUESTIONS
    
    @staticmethod
    def validate_answer(answer):
        """Validate security answer format"""
        if not answer or not isinstance(answer, str):
            return False, "Security answer is required"
        
        answer = answer.strip()
        if len(answer) < 1:
            return False, "Security answer cannot be empty"
        
        if len(answer) > 100:
            return False, "Security answer must be less than 100 characters"
        
        return True, "Valid answer"