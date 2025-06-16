import os
import re
import time
from dotenv import load_dotenv
import google.generativeai as genai

# Load API key from .env file
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    print("⚠️ Error: API_KEY not set in .env file.")
    exit(1)

genai.configure(api_key=API_KEY)

def load_books(filepath="books.txt"):
    books = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    title, author, description = line.strip().split("|")
                    books.append({
                        "title": title.strip(),
                        "author": author.strip(),
                        "description": description.strip()
                    })
                except ValueError:
                    continue
    except FileNotFoundError:
        print("⚠️ Error: 'books.txt' file not found.")
    return books

def search_books(books, keyword):
    keyword = keyword.lower()
    results = []
    for book in books:
        if (keyword in book['title'].lower() or
            keyword in book['author'].lower() or
            keyword in book['description'].lower()):
            results.append(book)
    return results

def ask_gemini(question, chat_history=None, retries=2):
    model_name = "gemini-1.5-flash"

    if chat_history:
        history_text = "\n".join(
            f"User: {q}\nBot: {a}" for q, a in chat_history
        )
        prompt = f"{history_text}\nUser: {question}"
    else:
        prompt = question

    for attempt in range(retries + 1):
        try:
            model = genai.GenerativeModel(model_name=model_name)
            response = model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            err_str = str(e)

            # Handle quota error (429 Too Many Requests)
            if "429" in err_str:
                print(f"⚠️ Gemini error ({model_name}): You exceeded your current quota.")

                # Try to extract retry delay from error message
                match = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)", err_str)
                retry_secs = int(match.group(1)) if match else 4  # default to 4 seconds

                if attempt < retries:
                    print(f"⏳ Waiting {retry_secs} seconds before retrying (attempt {attempt + 1}/{retries})...")
                    time.sleep(retry_secs)
                else:
                    print("❌ Max retries reached. Still over quota.")
                    return "⚠️ Sorry, I couldn’t connect to Gemini AI due to quota limits. Please try again later."
            else:
                print(f"⚠️ Gemini error ({model_name}): {err_str}")
                return "⚠️ Sorry, I couldn’t connect to Gemini AI right now. Please try again later."

    return "⚠️ Failed after retries."


def main():
    books = load_books()
    chat_history = []

    print("📚 Welcome to the Book ChatBot!")
    print("Type 'exit' to quit. Type 'history' to view previous messages.\n")

    while True:
        user_input = input("👤 You: ").strip()
        if user_input.lower() == "exit":
            print("🤖 Goodbye!")
            break
        elif user_input.lower() == "history":
            if chat_history:
                print("\n🕘 Chat History:")
                for i, (q, a) in enumerate(chat_history, 1):
                    print(f"{i}. You: {q}")
                    print(f"   Gemini: {a}\n")
            else:
                print("ℹ️ No chat history yet.")
            continue

        # Search for books if keywords detected
        if any(kw in user_input.lower() for kw in ["book", "novel", "author", "about", "story"]):
            results = search_books(books, user_input)
            if results:
                print(f"\n📘 Found {len(results)} result(s):")
                for book in results[:5]:
                    print(f"- {book['title']} by {book['author']}\n  {book['description']}\n")
                chat_history.append((user_input, "Provided book search results."))
            else:
                print("😔 No matching books found. Let me ask Gemini...")
                response = ask_gemini(user_input, chat_history)
                print("🤖 Gemini:", response)
                chat_history.append((user_input, response))
        else:
            response = ask_gemini(user_input, chat_history)
            print("🤖 Gemini:", response)
            chat_history.append((user_input, response))

if __name__ == "__main__":
    main()
