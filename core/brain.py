import ollama
from utils.constants import Settings

class AssistantBrain:
    def __init__(self):
        self.model_name = "llama3.2"
        # System instructions to keep Jarvis acting sharp and conversational
        self.history = [
            {
                "role": "system",
                "content": f"You are {Settings.ASSISTANT_NAME}, a highly efficient, crisp voice assistant. Keep answers brief, direct, and conversational.",
            }
        ]
        print(
            f"[Brain Engine Module: Local Ollama Model ({self.model_name}) Connected]"
        )

    def generate_response(
        self, user_input: str, complexity_tier: str, detected_lang: str
    ) -> tuple[str, str]:
        """Processes user input with dynamic speed parameters and preserves the language code."""

        # --- DYNAMIC OLLAMA SPEED TUNING ---
        if complexity_tier == "micro":
            ollama_options = {
                "temperature": 0.2,
                "num_predict": 45,  # Hard limit response length for ultra-low latency
                "top_k": 20,
                "num_ctx": 1024,  # Tiny memory profile = faster matrix math on CPU
            }
            print(
                "[Brain Triage: Micro Input | Speed Mode Active (Strict Token Capping)]"
            )

        elif complexity_tier == "conversational":
            ollama_options = {
                "temperature": 0.5,
                "num_predict": 120,  # Standard conversational text limit
                "top_k": 40,
                "num_ctx": 2048,
            }
            print(
                "[Brain Triage: Conversational Input | Standard Processing Mode Active]"
            )

        else:
            ollama_options = {
                "temperature": 0.7,
                "num_predict": 350,  # Allow deep, detailed paragraphs
                "num_ctx": 4096,  # Full analytical memory allocation
            }
            print(
                "[Brain Triage: Deep Context Input | High-Precision Analytical Mode Active]"
            )

        # Append user message to rolling session memory
        self.history.append({"role": "user", "content": user_input})

        try:
            # Query the local LLM with our accelerated options profile
            response = ollama.chat(
                model=self.model_name, messages=self.history, options=ollama_options
            )

            reply = response["message"]["content"].strip()

            # Save the response to history to maintain context continuity
            self.history.append({"role": "assistant", "content": reply})

            # RETURN BOTH: The generated reply text and the language code passed to it
            return reply, detected_lang

        except Exception as e:
            print(f"[Ollama Core Inference Exception: {e}]")
            return (
                "I encountered a processing drop in my neural engine clusters, sir.",
                "en",
            )
