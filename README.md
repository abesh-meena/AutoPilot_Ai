# AutoPilot AI – Browser Automation Agent

## 🚀 Overview
AutoPilot AI is an intelligent browser automation agent that performs human-like actions on websites using natural language commands. Control your browser with simple instructions in English or Hinglish.

## ✨ Features
- **Natural Language Processing**: Understands commands in English and Hinglish
- **Cross-Platform**: Works on all major browsers
- **AI-Powered**: Uses advanced AI for task planning
- **Open Source**: Fully customizable and extensible

## 🛠 Installation

### Prerequisites
- Python 3.8+
- Node.js 16+
- Chrome or any Chromium-based browser

### Backend Setup
```bash
# Clone the repository
git clone [https://github.com/yourusername/AutoPilot-AI.git](https://github.com/yourusername/AutoPilot-AI.git)
cd AutoPilot-AI

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# OR
source venv/bin/activate  # Linux/Mac

# Install dependencies
cd backend
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the backend
uvicorn app:app --reload


--------------------------------------------------------------
Chrome Extension Setup
Open Chrome and go to chrome://extensions/
Enable "Developer mode" (toggle in top-right)
Click "Load unpacked"
Select the 
extension
 folder
🏃‍♂️ Quick Start
Start the backend server
Load the Chrome extension
Click the extension icon and enter your command, for example:
"Open YouTube and search for music"
"Google par 'latest AI news' search karo"
"Scroll down and click the second link"
📂 Project Structure
AutoPilot-AI/
├── backend/          # FastAPI server
├── extension/        # Chrome extension
├── docs/             # Documentation
├── .env.example      # Environment variables template
└── README.md         # This file
🤝 Contributing
Fork the repository
Create your feature branch (git checkout -b feature/AmazingFeature)
Commit your changes (git commit -m 'Add some AmazingFeature')
Push to the branch (git push origin feature/AmazingFeature)
Open a Pull Request
📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

🙏 Acknowledgments
Thanks to all open-source contributors
Built with ❤️ for the developer community