import os
import json
from dotenv import load_dotenv
from crewai import Agent, Task, Crew

load_dotenv()


def test_backends():
    backends = ["ollama/llama3.1", "ollama/gemma2:9b", "gemini/gemini-2.5-flash"]

    # Reducir verbosidad de logs
    import logging

    logging.getLogger("litellm").setLevel(logging.CRITICAL)

    for b in backends:
        print(f"--- TEST: {b} ---")
        try:
            if "google_generative_ai" in b:
                os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")
            if "ollama" in b:
                os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
                os.environ["OPENAI_API_KEY"] = "ollama"

            a = Agent(role="Test", goal="Say hi", backstory="Test", llm=b)
            t = Task(description="Say hi", expected_output="Hi", agent=a)
            c = Crew(agents=[a], tasks=[t])
            try:
                res = c.kickoff()
                print(f"SUCCESS: {res}")
            except Exception as e:
                print(f"FAIL: {e}")
        except Exception as e:
            print(f"FAIL: {e}")
        print("\n")


if __name__ == "__main__":
    test_backends()
