from groq import Groq
from dotenv import load_dotenv
import os
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Different system prompts for different modes
MODES = {
    "explain": """You are a friendly Study Buddy AI in EXPLAIN MODE. Your role is to:
- Explain concepts in simple, easy-to-understand language
- Break down complex topics into smaller parts
- Use examples and analogies
- Be encouraging and patient
- Ask follow-up questions to check understanding""",
    
    "quiz": """You are a Study Buddy AI in QUIZ MODE. Your role is to:
- Generate quiz questions based on topics discussed
- Create multiple choice, true/false, and short answer questions
- Provide immediate feedback on answers
- Explain why answers are correct or incorrect
- Keep quizzes engaging and educational""",
    
    "review": """You are a Study Buddy AI in REVIEW MODE. Your role is to:
- Create concise study notes and summaries
- Highlight key points and important facts
- Organize information in a structured way
- Create memory aids like mnemonics
- Focus on what's most important to remember"""
}

current_mode = "explain"

def chat(message, conversation_history, mode):
    """Send a message and get a response"""
    
    conversation_history.append({
        "role": "user",
        "content": message
    })
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": MODES[mode]}
        ] + conversation_history,
        temperature=0.7,
        max_tokens=800
    )
    
    assistant_message = response.choices[0].message.content
    
    conversation_history.append({
        "role": "assistant",
        "content": assistant_message
    })
    
    return assistant_message

def save_session(conversation_history, topics_studied, mode):
    """Save the current study session to a file"""
    
    if not os.path.exists('study_sessions'):
        os.makedirs('study_sessions')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"study_sessions/session_{timestamp}.json"
    
    session_data = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "topics": topics_studied,
        "conversation": conversation_history
    }
    
    with open(filename, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    return filename

def load_sessions():
    """Load all past study sessions"""
    
    if not os.path.exists('study_sessions'):
        return []
    
    sessions = []
    for filename in os.listdir('study_sessions'):
        if filename.endswith('.json'):
            with open(f'study_sessions/{filename}', 'r') as f:
                sessions.append(json.load(f))
    
    return sessions

def get_summary(conversation_history, mode):
    """Generate a summary of the study session"""
    
    summary_prompt = "Based on our conversation, provide a brief summary of the main topics covered and key points learned. Keep it concise (3-5 bullet points)."
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": MODES[mode]}
        ] + conversation_history + [
            {"role": "user", "content": summary_prompt}
        ],
        temperature=0.7,
        max_tokens=300
    )
    
    return response.choices[0].message.content

def show_commands():
    """Display available commands"""
    print("\n📚 Study Buddy Commands:")
    print("  /help       - Show this help menu")
    print("  /mode       - Switch study mode (explain/quiz/review)")
    print("  /reset      - Start a new study session")
    print("  /save       - Save current study session")
    print("  /history    - Show past study sessions")
    print("  /summary    - Get summary of current session")
    print("  quit        - Exit and auto-save session\n")

def show_history():
    """Display past study sessions"""
    sessions = load_sessions()
    
    if not sessions:
        print("\n📝 No past study sessions found.\n")
        return
    
    print("\n📚 Past Study Sessions:")
    print("=" * 60)
    
    for i, session in enumerate(sessions[-5:], 1):
        print(f"\n{i}. Date: {session['date']}")
        print(f"   Mode: {session.get('mode', 'explain').upper()}")
        print(f"   Topics: {', '.join(session['topics']) if session['topics'] else 'No topics tracked'}")
        print(f"   Messages: {len(session['conversation'])} exchanges")
    
    print("\n" + "=" * 60 + "\n")

def change_mode(current_mode):
    """Change the study mode"""
    print("\n🔄 Available Modes:")
    print("  1. Explain Mode - Get clear explanations (default)")
    print("  2. Quiz Mode - Practice with quizzes")
    print("  3. Review Mode - Create study notes and summaries")
    
    choice = input("\nSelect mode (1/2/3): ").strip()
    
    mode_map = {
        "1": "explain",
        "2": "quiz",
        "3": "review"
    }
    
    new_mode = mode_map.get(choice, current_mode)
    
    mode_emojis = {
        "explain": "📖",
        "quiz": "❓",
        "review": "📝"
    }
    
    print(f"\n{mode_emojis[new_mode]} Switched to {new_mode.upper()} mode!\n")
    return new_mode

# Main chat loop
print("=" * 60)
print("📚 Study Buddy - Your AI Learning Companion")
print("=" * 60)
print("\nHi! I'm here to help you learn anything you want!")
print("Currently in EXPLAIN MODE 📖")
print("Type /help for commands or /mode to switch modes.\n")

conversation_history = []
topics_studied = []

while True:
    mode_emoji = {"explain": "📖", "quiz": "❓", "review": "📝"}[current_mode]
    user_input = input(f"You [{mode_emoji}]: ")
    
    # Handle quit with auto-save
    if user_input.lower() == 'quit':
        if conversation_history:
            print("\n💾 Saving your study session...")
            filename = save_session(conversation_history, topics_studied, current_mode)
            print(f"✅ Session saved to {filename}")
        print("\n👋 Keep up the great studying! See you next time!")
        break
    
    # Handle commands
    if user_input.lower() == '/help':
        show_commands()
        continue
    
    if user_input.lower() == '/mode':
        current_mode = change_mode(current_mode)
        continue
    
    if user_input.lower() == '/reset':
        if conversation_history:
            save_choice = input("\n💾 Save current session before resetting? (y/n): ")
            if save_choice.lower() == 'y':
                filename = save_session(conversation_history, topics_studied, current_mode)
                print(f"✅ Session saved to {filename}")
        
        conversation_history = []
        topics_studied = []
        print("\n🔄 New study session started! What would you like to learn?\n")
        continue
    
    if user_input.lower() == '/save':
        filename = save_session(conversation_history, topics_studied, current_mode)
        print(f"\n✅ Session saved to {filename}\n")
        continue
    
    if user_input.lower() == '/history':
        show_history()
        continue
    
    if user_input.lower() == '/summary':
        if not conversation_history:
            print("\n📝 No conversation to summarize yet. Start studying first!\n")
            continue
        
        print("\n📊 Generating summary...\n")
        summary = get_summary(conversation_history, current_mode)
        print(f"📖 Session Summary:\n{summary}\n")
        continue
    
    if not user_input.strip():
        continue
    
    # Track topics
    if any(word in user_input.lower() for word in ['explain', 'what is', 'tell me about', 'how does']):
        for word in ['explain', 'what is', 'tell me about', 'how does', 'why']:
            if word in user_input.lower():
                topic = user_input.lower().replace(word, '').strip()
                if topic and len(topic) > 3:
                    topics_studied.append(topic)
                break
    
    try:
        response = chat(user_input, conversation_history, current_mode)
        print(f"\n{mode_emoji} Study Buddy: {response}\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Try again or type /help for commands\n")