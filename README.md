cat << 'EOF' > README.md
# 🚢 Averis Nexus AI: Maritime Document Intelligence Hub

An enterprise-grade AI pipeline and interactive dashboard designed for the **Averis Hackathon 2026**. This system automates the classification of shipping emails, extracts data from local Shipping Instructions (SI) and Bill of Lading (BL) documents, and detects critical data discrepancies.

Powered by **100% Groq AI Backend** (bypassing standard API token limits) and a **Midnight Glass Streamlit Dashboard**, ensuring sensitive data is processed locally, quickly, and securely.

---

## ⚙️ 1. Prerequisites

Before starting, ensure you have the following installed on your machine:
1. **Python 3.12+**: For running the AI script and web dashboard.
2. **Docker Desktop**: Required to run the local Hackathon Evaluation Server.
3. **Groq API Key**: A free API key from [console.groq.com](https://console.groq.com).

---

## 🛠️ 2. First-Time Setup & Installation

### Step A: Configure the API Key
You must provide the system with a Groq API key to process the text.
1. Open the `shipping-verification-project` folder.
2. Create a new file named exactly **`.env`** (do not name it `env` or `.env.txt`).
3. Open the file and add your key like this:

    GROQ_API_KEY=your_actual_api_key_here

### Step B: Create a Virtual Environment
To prevent dependency conflicts, set up a Python virtual environment. Open a terminal, navigate to the `shipping-verification-project` folder, and run:

    # Create the virtual environment
    python -m venv venv

    # Activate it (Mac/Linux)
    source venv/bin/activate

*(You should see `(venv)` appear at the start of your terminal prompt).*

### Step C: Install Dependencies
With the virtual environment active, install all required packages:

    pip install groq pydantic python-dotenv streamlit pandas openpyxl docx2txt requests plotly fpdf watchdog

---

## 🚀 3. How to Run the System (The Dual-Terminal Setup)

This project requires **two separate terminal windows** running simultaneously: one for the Docker Evaluation Server, and one for the AI Web Dashboard.

### Terminal 1: Start the Docker Scoreboard
1. Open a new terminal window.
2. Navigate to the folder containing the `docker-compose.yml` file (typically `sdoc-hackathon-docker`).

    cd path/to/sdoc-hackathon-docker

3. Boot up the server:

    docker compose up --build

4. **Leave this terminal open and running in the background.**

### Terminal 2: Start the Web Dashboard
1. Open a **second** terminal window.
2. Navigate to your Python project folder:

    cd path/to/shipping-verification-project

3. **Activate the virtual environment** (Crucial!):

    source venv/bin/activate

4. Launch the application:

    streamlit run app.py

5. The Averis Nexus AI dashboard will automatically open in your web browser at `http://localhost:8501`.

---

## 🖥️ 4. How to Use the Dashboard

Once the website is open in your browser, use the sidebar to control the system:

1. **Scan Volume Limit**: Use the dropdown in the sidebar to choose how many emails to process (e.g., 5 emails for a quick test, or "All" for the full 520 dataset).
2. **Start AI Scanner**: Click the primary button to begin. You will see a live progress bar and a **Real-Time ETA Calculator** showing exactly how long the batch will take.
3. **Analytics (Tab 1)**: View live Plotly charts breaking down category routing and data discrepancy frequencies.
4. **Audit Trail (Tab 2)**: Search for specific emails and view side-by-side comparisons highlighting exactly what data failed to match between the SI and BL documents.
5. **Evaluation Server (Tab 3)**: Click the "Submit" button to push your results to the Docker server running in Terminal 1 and receive your official Hackathon Score.
6. **Executive PDF Report**: Click the "Download PDF Report" button in the sidebar to generate a professional summary of the pipeline's findings.

---

## 🛑 5. How to Stop and End the Session

When you are completely finished working, you must shut down both servers gracefully to free up your computer's memory.

1. **Stop the Website**: Go to **Terminal 2**, click inside the window, and press `Ctrl + C`. This stops Streamlit.
2. **Stop the Docker Server**: Go to **Terminal 1**, click inside the window, and press `Ctrl + C`. Once it stops logging, type the following command to completely tear down the containers:

    docker compose down

---

## ⚠️ 6. Common Troubleshooting

* **Error: `no configuration file provided: not found` (Docker)**
  * *Cause*: You tried to run `docker compose up` while inside the Python folder.
  * *Fix*: `cd` into the `sdoc-hackathon-docker` folder first, then run the command.

* **Error: `zsh: command not found: streamlit` or `pip`**
  * *Cause*: Your virtual environment is not active.
  * *Fix*: Run `source venv/bin/activate` (or `source ../venv/bin/activate` depending on your path) before running the command.

* **Log Warning: `429 Too Many Requests` or `Retrying request...`**
  * *Cause*: The Groq AI is processing data so fast that it temporarily hit the free-tier speed limit.
  * *Fix*: **Do nothing!** This is expected behavior. The script is designed to automatically pause and retry gracefully without crashing.

* **Dashboard frozen or buttons not working**
  * *Fix*: Go to the sidebar and click **"🔄 Refresh Dashboard"**, or refresh your browser tab.
EOF
