import ollama
from prompts import SYSTEM_PROMPT

def create_llama3_model():
    model_name = "llama3:8b"
    
    user_prompt = "hi who are you"
    
    model = ollama.create(
        model=model_name,
        system=SYSTEM_PROMPT,
        user=user_prompt
    )
    
    return model

if __name__ == "__main__":
    model = create_llama3_model()
    print("Llama3.2 model created successfully with the custom system and user prompt.")
