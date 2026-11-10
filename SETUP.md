# AI Interviewer - Setup Guide

This guide explains how to set up and run the AI Interviewer project on your local machine.

---

## Prerequisites

Make sure the following software is installed:

- Node.js (v18 or later)
- npm
- Python 3.10 or later
- Git

---

## 1. Clone the Repository

```bash
git clone https://github.com/Mohit7089/AI_INTERVIEWER.git
cd AI_INTERVIEWER
```

---

## 2. Install Dependencies

### Root

```bash
npm install
```

### Frontend

```bash
cd client
npm install
```

### Backend

```bash
cd ../server
npm install
```

### Resume Analyzer (Flask API)

```bash
cd ../resume-analyzer-api

python3 -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
# venv\Scripts\activate

pip install -r requirements.txt
```

---

## 3. Frontend Environment

The required frontend environment configuration (`client/.env`) is already included in the repository.

No additional Firebase setup is required.

---

## 4. Backend Environment Variables

Create a file named:

```
server/.env
```

Add the following variables:

```env
PORT=8000

MONGODB_URI=YOUR_MONGODB_CONNECTION_STRING

JWT_SECRET=YOUR_JWT_SECRET

OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY

CLIENT_URL=http://localhost:5173
```

Replace the placeholder values with your own credentials.

---

## 5. Run the Project

Return to the project root.

```bash
cd ..
npm run dev
```

This command starts:

- React Frontend
- Express Backend
- Flask Resume Analyzer

---

## Project Structure

```
AI_INTERVIEWER/
│
├── client/
├── server/
├── resume-analyzer-api/
├── package.json
├── SETUP.md
└── .gitignore
```

---

## Common Issues

### Python Packages Missing

```bash
cd resume-analyzer-api

source venv/bin/activate

pip install -r requirements.txt
```

---

### Port 5000 Already in Use

```bash
kill -9 $(lsof -ti:5000)
```

---

### Port 5173 Already in Use

```bash
kill -9 $(lsof -ti:5173)
```

---

### Node Modules Missing

Run the following command inside the required folder:

```bash
npm install
```

---

## Notes

- Do **not** commit `server/.env` because it contains sensitive credentials.
- The frontend environment (`client/.env`) is already included in this repository.
- If you change backend credentials, update `server/.env` accordingly before running the project.