# AI-Based Placement Practice & MCQ Intelligence Platform

**AI-Based Placement Practice** is an interactive platform designed to help students prepare for placement tests using AI-generated MCQs. It leverages company-specific data to generate personalized quizzes and provides detailed feedback to identify strengths and weaknesses.

---

## Features

### 1. Modern Dashboard
- High-level overview of key performance indicators.
- Clear explanation of the platform's utility.
- Professional UI with modern typography and interactive cards.

![Dashboard Screenshot](frontend/screenshot-dashboard.png)

---

### 2. Admin Workflow
- **Company File Upload**: Supports document uploads with real-time feedback and loaders.
- **Data Ingestion**: Multi-step process for preparing uploaded data for RAG-based MCQ generation.
- Shows detailed processing stats for each data chunk.

![Admin Workflow Screenshot](frontend/screenshot-admin.png)

---

### 3. Student Workflow
- **MCQ Generation**: Personalized questions by topic (Aptitude, English, Debugging) and company data.
- **Interactive Testing**: SPA-style test environment with progress tracking.
- **AI Feedback**: Post-test analysis highlighting strengths, weaknesses, and suggested improvements.

![Student Test Screenshot](frontend/screenshot-student.png)

---

### 4. Verification & Navigation
- All sidebar links navigate correctly without page reloads (SPA behavior).
- Answers, scores, and page states are preserved during interactions.
- Forms handle simulated API latencies with loaders and status messages.

![Verification Screenshot](frontend/screenshot-verification.png)

---

### 5. Visual Excellence
- Consistent **Inter typography**.
- Rounded corners (12px), soft shadows, and professional blue/gray/success palette.
- Hover states on interactive elements.
- Clean and modern UI for both admin and student workflows.

---

## How to Run

### Option A: Open Directly
- Open `index.html` in your preferred web browser (Chrome, Edge, or Firefox).

### Option B: Local Development Server
For a better experience, serve the files using a local server. For example, with Python:

```bash
cd C:/Users/ahari/OneDrive/Desktop/test-1/frontend
python -m http.server 8000
