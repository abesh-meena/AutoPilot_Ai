# AutoPilot AI - Deployment Guide

## Overview
AutoPilot AI consists of two main components:
1. **FastAPI Backend** - AI task planning and execution server
2. **Chrome Extension** - Browser automation interface

## Backend Deployment

### Option 1: Docker (Recommended)
```bash
# Clone and navigate to project
cd Autopilot_Ai

# Build and run with Docker Compose
docker-compose up -d

# Check status
docker-compose ps
```

### Option 2: Manual Deployment
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the server
uvicorn app:app --host 0.0.0.0 --port 8000
```

### Environment Variables
Create `.env` file in backend directory:
```
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
ANTHROPIC_API_KEY=your_anthropic_key
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## Chrome Extension Deployment

### Development Installation
1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `extension` folder

### Production Build
1. Install Node.js dependencies in extension folder:
   ```bash
   cd extension
   npm install archiver
   ```

2. Build the extension:
   ```bash
   node build-extension.js
   ```

3. Upload `autopilot-extension.zip` to Chrome Web Store

### Chrome Web Store Submission
- Prepare store listing with screenshots
- Set appropriate permissions and content policies
- Test thoroughly before submission

## Production Considerations

### Security
- Use HTTPS for backend API
- Implement API rate limiting
- Secure API keys in environment variables
- Consider API gateway for additional security

### Scaling
- Backend can be horizontally scaled behind load balancer
- Consider Redis for session management
- Monitor API usage and costs

### Monitoring
- Set up health checks on backend
- Monitor extension performance
- Track user analytics (with privacy compliance)

## Troubleshooting

### Backend Issues
- Check logs: `docker-compose logs autopilot-backend`
- Verify environment variables
- Test API endpoints with curl/Postman

### Extension Issues
- Check Chrome developer console for errors
- Verify backend URL in extension code
- Test permissions in manifest.json

## URLs
- Backend API: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`
