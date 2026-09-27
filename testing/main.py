# Gemini starter kept for later backend work. The working agent is agent.py.

# import os
# import google.generativeai as genai
# from dotenv import load_dotenv
# from google.generativeai import types
# from functions.get_files_info import get_files_info
#
# def main():
#     load_dotenv()
#     api_key = os.getenv("GEMINI_API_KEY")
#     genai.configure(api_key=api_key)
#     model = genai.GenerativeModel("gemini-2.0-flash")
#     user = input("please enter the prompt: ")
#     response = model.generate_content(user)
#     print(response.text)
#
# if __name__ == "__main__":
#     main()
