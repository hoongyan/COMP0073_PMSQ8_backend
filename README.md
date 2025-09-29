# Project

This repository provides the code for the backend server of the ScamOrion website for COMP0073 MSc Computer Science Project.

## Setup Prerequisites

Prior to setting up the repository for use, please ensure that the following prerequisites have been installed into the environment.

- **Python 3.13.5** - If not installed, install this version from the [Python official website](https://www.python.org/).
- **Ollama**
  - To install Ollama for running models locally, visit [https://github.com/ollama/ollama](https://github.com/ollama/ollama) and follow the instructions for your operating system.
  - After installation, open a new terminal (in VS Code or your desktop interface) and start the Ollama service with the command `ollama serve`. Keep this terminal open to ensure Ollama runs in the background at all times.
  - Next, install the required models for the research repository using the command `ollama pull <modelname>` (replace `<modelname>` with each one below):
    - qwen2.5:7b
    - granite3.2:8b
    - mistral:7b
  - Verify models with `ollama list`. If pull fails, check internet and disk space.
- Git (for cloning the repository)
- Make (ensure it's installed on your system)
- PostgreSQL with pgvector extension (will be set up via Makefile)
- Optional: Access to OpenAI API for model integrations

## Installation Steps

1. **Clone the Repository**  
   Clone or copy the code repository and navigate to the project directory:

```
   git clone <repository-url>

   cd <project-directory>
```

2. **Configure Environment Variables**  
   Create a `.env` file in the project root and add the required environment variables. Refer to the `COMP0073 Environment Variables PMSQ8.docx` (available in the supporting documents `PMSQ8.zip`) for templates.  
   Key variables include:

- **PostgreSQL + pgvector Database:**
  - `POSTGRES_USER`
  - `POSTGRES_PASSWORD`
  - `POSTGRES_DB`
  - `POSTGRES_PORT`
  - `DATABASE_URL` (e.g., `postgresql://user:password@localhost:port/db_name`)
- **Local and Remote Models Setup:**
  - `OPENAI_API_KEY`
  - `OLLAMA_BASE_URL` (Optional, for local models)
- **Client-Related Variables:**

  - `FRONTEND_URL`: Set to match your local client (default: `http://localhost:3000`)
  - `SECRET_KEY`: Generate a secure random string using:

```
    python -c 'import secrets; print(secrets.token_hex(32))'
```

3. **Create and Activate Virtual Environment**  
   Create a new virtual environment:
   ```
   python -m venv myenv
   ```

Verify the Python version:

```
   python --version
```

4. **Install Dependencies**
   Run:

   ```
   make install
   ```

5. **Set Up Database and Start Server**
   Set up PostgreSQL + pgvector (including populating data) and start the FastAPI server:

   ```
   make setup
   ```

6. **Verify the Setup**
   Access the FastAPI documentation at:
   [http://localhost:8000/docs](http://localhost:8000/docs)
   If you encounter issues, check the logs for port conflicts or missing dependencies.


