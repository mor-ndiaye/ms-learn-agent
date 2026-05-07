"""Example: ask the advisor a question."""

from agent import agent_loop

if __name__ == "__main__":
    response = agent_loop(
        "I want to learn Azure Machine Learning fundamentals, intermediate level"
    )
    print(response)
