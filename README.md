ContextualAI-Docs: AI-Powered Document Management & Chat 📚💬
This project provides an intelligent platform for users to manage their documents and interact with their content using a conversational AI. Leverage Retrieval-Augmented Generation (RAG) to get precise, context-aware answers from your uploaded files.

✨ Features
Document Upload & Management: Securely upload and store various document types (PDF, DOCX, TXT, MD).

Intelligent AI Chat: Ask questions about your documents and receive answers grounded in their content.

Real-time Interaction: Instant AI responses via WebSockets for a fluid chat experience.

Source Citation: AI responses provide citations back to the source documents.

Conversational History: Your chat sessions are stored for easy access.

Scalable Architecture: Built with Django, React, Channels, Pinecone, and Gemini API.

🚀 Getting Started
Follow these steps to set up and run the application locally.

📝 Prerequisites
Ensure you have the following installed on your system:

Python 3.10+

Node.js & npm/yarn (LTS version recommended)

Git

Redis Server: Install and run a Redis server locally. On Windows, you can use WSL2 or a Docker container.

Pinecone Account & Index: You'll need a Pinecone API Key, Environment, and an active Pinecone index (dimension 384, metric 'cosine').

Google Gemini API Key: Obtain a Gemini API Key from Google AI Studio.

<br/>

📦 Setup
1. Clone the Repository
git clone https://github.com/jahnavi0102/ContextualAI-Docs.git
cd ContextualAI-Docs

2. Backend Setup (backend/ directory)
Navigate into the backend directory:

cd backend

a. Create and Activate Virtual Environment
It's highly recommended to use a virtual environment to manage Python dependencies.

python -m venv linenv
# On Windows:
.\linenv\Scripts\activate
# On macOS/Linux:
source linenv/bin/activate

b. Install Python Dependencies
pip install -r requirements.txt
# Ensure you have the full uvicorn[standard] for WebSocket support
pip install 'uvicorn[standard]'

c. Create .env File
Create a file named .env in the backend/ directory (same level as manage.py) and populate it with your environment variables. Do NOT commit this file to Git.

# .env (example content - replace with your actual values)

SECRET_KEY='YOUR_DJANGO_SECRET_KEY' # Generate a strong one, e.g., using: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Database (for local PostgreSQL, if used, otherwise configure your default for sqlite3 or a local Docker Postgres)
# If using PostgreSQL locally (e.g., via Docker), replace with your connection string:
# DATABASE_URL=postgres://user:password@host:port/dbname
# For SQLite (default development database):
DATABASE_URL=sqlite:///./db.sqlite3

# Redis for Channels and RQ
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your_redis_password # Uncomment if your local Redis requires a password

# Pinecone Credentials
PINECONE_API_KEY='YOUR_PINECONE_API_KEY'
PINECONE_ENVIRONMENT='YOUR_PINECONE_ENVIRONMENT' # e.g., 'us-east-1'
PINECONE_INDEX_NAME='rag-document-index' # Ensure this index exists in your Pinecone account with dimension 384

# Gemini API Key (ensure it matches the key for 'gemini-2.0-flash')
GEMINI_API_KEY='YOUR_GEMINI_API_KEY'

# Frontend URL (for CORS) - Use your Netlify URL in production
CORS_ALLOWED_ORIGINS=http://localhost:3000

d. Run Django Migrations
Apply database schema changes:

python manage.py migrate

e. Download Embedding Model
The sentence-transformers model will automatically download when your backend server (Daphne/Uvicorn) or RQ worker starts for the first time. This can take a few minutes depending on your internet connection.

3. Frontend Setup (frontend/ directory)
Navigate into the frontend directory:

cd ../frontend

a. Install Node.js Dependencies
npm install
# or
yarn install

4. Configure Frontend API Base URL
In your frontend directory, create a .env.local file (or directly in your package.json scripts) to set the API base URL for development.

# frontend/.env.local (for local development)
REACT_APP_API_BASE_URL=http://127.0.0.1:8000

Important for Deployment: When deploying to Netlify, you'll configure REACT_APP_API_BASE_URL in Netlify's build settings to point to your Render backend's URL.

▶️ Running the Application Locally
You'll need three separate terminal windows open, each running a different component:

Terminal 1: Start Backend ASGI Server (HTTP & WebSockets)
Navigate to the backend/ directory. Use Uvicorn for full ASGI and WebSocket support.

cd backend
uvicorn document_management.asgi:application --port 8000 --ws websockets --reload

This command ensures auto-reloading during development.

Terminal 2: Start RQ Worker (Background Tasks)
Navigate to the backend/ directory.

cd backend
python manage.py rqworker default

This worker processes document uploads and other background tasks.

Terminal 3: Start Frontend Development Server
Navigate to the frontend/ directory.

cd frontend
npm start
# or
yarn start

This will open your React app in your browser, usually at http://localhost:3000.

🗑️ .gitignore Configuration
Ensure your project's .gitignore file (at the root of your repository) includes the following to prevent unnecessary files from being committed:

# Virtual Environment
backend/linenv/

# Node Modules
frontend/node_modules/

# Environment Variable Files
backend/.env

# Python Cache Directories
backend/analytics/__pycache__/
backend/chat/__pycache__/
backend/document_management/__pycache__/
backend/documents/__pycache__/
backend/users/__pycache__/

# Uploaded Media Files (for documents, etc.)
backend/media/

🐛 Troubleshooting
"Address already in use": Ensure no other application is using port 8000 (for backend) or 3000 (for frontend).

"No supported WebSocket library detected": Ensure you've run pip install 'uvicorn[standard]'.

Database Errors (ProgrammingError): Run python manage.py makemigrations and python manage.py migrate from the backend/ directory.

"NUL (0x00) characters" error during document processing: Ensure your backend/documents/tasks.py includes the file_content.replace('\x00', '') line, and restart your RQ worker.

AI says "I don't have enough information":

Check your rqworker logs to ensure documents completed processing successfully.

Add debug prints to backend/chat/views.py (SendMessageView) to inspect Pinecone query results and the prompt sent to Gemini.

Verify your Pinecone index has the correct dimensions (384 for all-MiniLM-L6-v2) and relevant data.

Ensure your GEMINI_API_KEY is valid and has access to gemini-2.0-flash.

Frontend errors related to API calls: Verify REACT_APP_API_BASE_URL in your frontend/.env.local is correct, and check browser console for network errors.

☁️ Deployment
Not deployed