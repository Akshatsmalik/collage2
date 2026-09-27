"""Run the coding agent. Same as `python agent.py`."""

from agent import run_agent

if __name__ == "__main__":
    user = input("Please enter your task: ")
    run_agent(user)
    print("\nDONE")
