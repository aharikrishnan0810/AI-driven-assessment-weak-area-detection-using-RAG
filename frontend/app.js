/**
 * Placement Practice AI Platform - Core Logic
 */

const app = {
    currentPage: 'dashboard',
    companies: [],
    mcqs: [],
    currentMCQIndex: 0,
    userAnswers: [],
    stats: {
        mcqsGenerated: 0,
        testsCompleted: 0
    },

    async init() {
        if (window.location.protocol === 'file:') {
            alert("CRITICAL ERROR: You are opening index.html directly as a file. The portal will NOT work. \n\nPlease close this and open http://localhost:8001 in your browser instead.");
            document.body.innerHTML = `<div style="padding: 2rem; text-align: center; color: #dc2626; font-family: sans-serif;">
                <h1 style="font-size: 2rem;">🛑 Wrong URL!</h1>
                <p>You opened the file directly. You <b>MUST</b> use the server URL:</p>
                <div style="background: #fee2e2; padding: 1rem; border-radius: 8px; font-size: 1.5rem; margin: 1rem auto; max-width: 400px; border: 1px solid #f87171;">
                    <a href="http://localhost:8001">http://localhost:8001</a>
                </div>
                <p>Ensure <code>python gemini_qa.py</code> is running in your terminal.</p>
            </div>`;
            return;
        }
        this.cacheDOM();
        this.bindEvents();
        await this.fetchCompanies();
        this.renderPage('dashboard');
    },

    cacheDOM() {
        this.mainContent = document.getElementById('mainContent');
        this.pageTitle = document.getElementById('pageTitle');
        this.navItems = document.querySelectorAll('.nav-item');
    },

    bindEvents() {
        this.navItems.forEach(item => {
            item.addEventListener('click', () => {
                const page = item.getAttribute('data-page');
                this.navigate(page);
            });
        });
    },

    async fetchCompanies() {
        try {
            const res = await fetch('/admin/companies');
            if (res.ok) {
                this.companies = await res.json();
            }
        } catch (err) {
            console.error('Failed to fetch companies', err);
        }
    },

    navigate(pageId) {
        this.currentPage = pageId;
        this.navItems.forEach(item => {
            item.classList.toggle('active', item.getAttribute('data-page') === pageId);
        });

        const names = {
            dashboard: 'Dashboard',
            upload: 'Upload Company File',
            ingest: 'Ingest Company Data',
            generate: 'Generate MCQs',
            'take-test': 'Practice Test',
            results: 'Test Results'
        };
        this.pageTitle.textContent = names[pageId] || 'PlacementAI';
        this.renderPage(pageId);
    },

    renderPage(pageId) {
        const template = document.getElementById(`tpl-${pageId}`);
        if (!template) return;

        this.mainContent.innerHTML = '';
        const clone = template.content.cloneNode(true);
        this.mainContent.appendChild(clone);

        if (pageId === 'dashboard') this.initDashboardPage();
        if (pageId === 'upload') this.initUploadPage();
        if (pageId === 'ingest') this.initIngestPage();
        if (pageId === 'generate') this.initGeneratePage();
        if (pageId === 'take-test') this.initTestPage();
        if (pageId === 'results') this.initResultsPage();
    },

    initDashboardPage() {
        document.getElementById('count-companies').textContent = this.companies.length;
    },

    // --- Page Initialization Logic ---

    initUploadPage() {
        const form = document.getElementById('uploadForm');
        form.onsubmit = async (e) => {
            e.preventDefault();
            const company = document.getElementById('companyName').value;
            const file = document.getElementById('companyFile').files[0];
            const loader = document.getElementById('uploadLoader');
            const status = document.getElementById('uploadStatus');

            loader.classList.remove('hidden');
            status.innerHTML = '';

            const formData = new FormData();
            formData.append('company', company);
            formData.append('file', file);

            try {
                const res = await fetch('/admin/upload', { method: 'POST', body: formData });
                if (res.ok) {
                    status.innerHTML = `<div class="alert alert-success">Company "${company}" file uploaded successfully!</div>`;
                    form.reset();
                    await this.fetchCompanies();
                } else {
                    const errorData = await res.json().catch(() => ({}));
                    status.innerHTML = `<div class="alert alert-error">Upload failed: ${errorData.detail || res.statusText}</div>`;
                }
            } catch (err) {
                console.error('Upload Error:', err);
                status.innerHTML = `<div class="alert alert-error">Connection error: ${err.message}. Ensure the backend is running.</div>`;
            } finally {
                loader.classList.add('hidden');
            }
        };
    },

    initIngestPage() {
        const select = document.getElementById('ingestCompany');
        const form = document.getElementById('ingestForm');

        this.companies.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c; opt.textContent = c;
            select.appendChild(opt);
        });

        form.onsubmit = async (e) => {
            e.preventDefault();
            const company = select.value;
            const loader = document.getElementById('ingestLoader');
            const resultCard = document.getElementById('ingestResultCard');

            loader.classList.remove('hidden');
            resultCard.classList.add('hidden');

            try {
                const res = await fetch(`/admin/ingest?company=${encodeURIComponent(company)}`, { method: 'POST' });
                const data = await res.json();
                if (res.ok) {
                    document.getElementById('chunkCount').textContent = data.chunks;
                    resultCard.classList.remove('hidden');
                } else {
                    alert('Ingestion failed: ' + (data.detail || res.statusText));
                }
            } catch (err) {
                console.error('Ingest Error:', err);
                alert('Connection error: ' + err.message);
            }
            finally { loader.classList.add('hidden'); }
        };
    },

    initGeneratePage() {
        const form = document.getElementById('generateForm');
        const companySelect = document.getElementById('genCompany');

        this.companies.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c; opt.textContent = c;
            companySelect.appendChild(opt);
        });

        form.onsubmit = async (e) => {
            e.preventDefault();
            const loader = document.getElementById('genLoader');
            const company = companySelect.value;
            const topic = document.getElementById('genTopic').value;
            const count = parseInt(document.getElementById('genCount').value);

            loader.classList.remove('hidden');

            try {
                const endpoint = company ? '/generate-mcqs-rag' : '/generate-mcqs';
                const body = company ? { company, topic, parts: { [topic]: count } } : { topic, parts: { [topic]: count } };

                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });
                const data = await res.json();

                if (res.ok) {
                    this.processMCQResponse(data.mcqs || data);
                    this.stats.mcqsGenerated += this.mcqs.length;
                    this.navigate('take-test');
                } else {
                    const errorData = await res.json().catch(() => ({}));
                    alert('Generation failed: ' + (errorData.detail || res.statusText));
                }
            } catch (err) {
                console.error('Generation Error:', err);
                alert('Connection error: ' + err.message);
            }
            finally { loader.classList.add('hidden'); }
        };
    },

    processMCQResponse(mcqData) {
        this.mcqs = [];
        for (const section in mcqData) {
            if (Array.isArray(mcqData[section])) {
                mcqData[section].forEach(q => {
                    this.mcqs.push({
                        topic: section,
                        question: q.question,
                        options: [q.options.A, q.options.B, q.options.C, q.options.D],
                        correct: q.answer === 'A' ? 0 : q.answer === 'B' ? 1 : q.answer === 'C' ? 2 : 3,
                        explanation: q.explanation
                    });
                });
            }
        }
        this.currentMCQIndex = 0;
        this.userAnswers = new Array(this.mcqs.length).fill(null);
    },

    initTestPage() {
        if (this.mcqs.length === 0) { this.navigate('generate'); return; }
        this.renderQuestion();
        document.getElementById('prevQ').onclick = () => this.changeQuestion(-1);
        document.getElementById('nextQ').onclick = () => this.changeQuestion(1);
        document.getElementById('submitTest').onclick = () => this.submitTest();
    },

    renderQuestion() {
        const q = this.mcqs[this.currentMCQIndex];
        const container = document.getElementById('optionsList');

        document.getElementById('currentQNum').textContent = `Question ${this.currentMCQIndex + 1} of ${this.mcqs.length}`;
        document.getElementById('testProgress').style.width = `${((this.currentMCQIndex + 1) / this.mcqs.length) * 100}%`;
        document.getElementById('questionText').textContent = q.question;

        container.innerHTML = '';
        q.options.forEach((opt, idx) => {
            const div = document.createElement('div');
            div.className = `option-item ${this.userAnswers[this.currentMCQIndex] === idx ? 'selected' : ''}`;
            div.innerHTML = `<input type="radio" class="option-radio" name="opt" ${this.userAnswers[this.currentMCQIndex] === idx ? 'checked' : ''}> <span>${opt}</span>`;
            div.onclick = () => {
                this.userAnswers[this.currentMCQIndex] = idx;
                this.renderQuestion();
                this.checkTestCompletion();
            };
            container.appendChild(div);
        });

        document.getElementById('prevQ').disabled = (this.currentMCQIndex === 0);
        document.getElementById('nextQ').classList.toggle('hidden', this.currentMCQIndex === this.mcqs.length - 1);
        this.checkTestCompletion();
    },

    changeQuestion(dir) {
        const next = this.currentMCQIndex + dir;
        if (next >= 0 && next < this.mcqs.length) {
            this.currentMCQIndex = next;
            this.renderQuestion();
        }
    },

    checkTestCompletion() {
        const allAnswered = this.userAnswers.every(a => a !== null);
        const isLast = (this.currentMCQIndex === this.mcqs.length - 1);
        document.getElementById('submitTest').classList.toggle('hidden', !(isLast && allAnswered));
    },

    submitTest() {
        let correctCount = 0;
        this.mcqs.forEach((q, idx) => { if (this.userAnswers[idx] === q.correct) correctCount++; });
        this.testResults = { score: Math.round((correctCount / this.mcqs.length) * 100), correct: correctCount, total: this.mcqs.length };
        this.stats.testsCompleted++;
        this.navigate('results');
    },

    async initResultsPage() {
        if (!this.testResults) { this.navigate('dashboard'); return; }
        const { score, correct, total } = this.testResults;
        document.getElementById('resScore').textContent = `${score}%`;
        document.getElementById('resCorrect').textContent = `${correct}/${total}`;

        try {
            const topic = this.mcqs[0]?.topic || "General";
            const res = await fetch('/generate-feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic, total_correct: correct, total_questions: total, sections: { [topic]: { correct, total } } })
            });
            const data = await res.json();
            document.getElementById('resMsg').textContent = data.overall_feedback || "Analysis complete.";
            const suggestions = document.getElementById('resSuggestions');
            suggestions.innerHTML = '';
            for (const section in data.section_feedback) {
                const li = document.createElement('li'); li.textContent = data.section_feedback[section];
                suggestions.appendChild(li);
            }
        } catch (err) { document.getElementById('resMsg').textContent = "Feedback unavailable."; }
    }
};

document.addEventListener('DOMContentLoaded', () => app.init());
