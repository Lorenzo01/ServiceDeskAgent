/* static/js/main.js */
document.addEventListener('DOMContentLoaded', () => {
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const resetBtn = document.getElementById('reset-btn');
    const pdfPanel = document.getElementById('pdf-panel');
    const pdfFrame = document.getElementById('pdf-frame');
    const pdfTitle = document.getElementById('pdf-title');
    const closePdfBtn = document.getElementById('close-pdf');
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const emailSupportBtn = document.getElementById('email-support-btn');
    const welcomeScreen = document.getElementById('welcome-screen');
    const messagesList = document.getElementById('messages-list');

    let isProcessing = false;
    let chatHistory = []; // Store chat history for email

    // Theme Toggle Logic
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            document.body.classList.toggle('light-mode');
            const isLight = document.body.classList.contains('light-mode');
            themeToggleBtn.textContent = isLight ? '🌙' : '☀️';
        });
    }

    // Email Support Logic
    // Email Support Logic
    const handleEmailSupport = async (e, btn) => {
        e.preventDefault();

        const originalText = btn.textContent;
        btn.textContent = "Generating Summary...";
        btn.style.pointerEvents = 'none'; // Disable clicks
        btn.style.cursor = 'wait';

        try {
            // Prepare history payload
            const historyPayload = chatHistory.map(msg => ({
                role: msg.role,
                content: msg.text
            }));

            // Get AI Summary
            const response = await fetch('/summarize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ history: historyPayload })
            });
            const data = await response.json();
            const summary = data.summary || "Summary unavailable.";

            const subject = encodeURIComponent("AskRecordSystem Support Request");
            let bodyText = `Dear RecordSystem Service Desk,\n\nI am encountering an issue and would like assistance.\n\n--- AI SUMMARY OF ISSUE ---\n${summary}\n\n--- FULL CHAT TRANSCRIPT ---\n`;

            if (chatHistory.length === 0) {
                bodyText += "(No chat history available)";
            } else {
                chatHistory.forEach(msg => {
                    const role = msg.role === 'User' ? 'User' : 'AskRecordSystem';
                    // Simple cleanup of markdown for email readability
                    const cleanText = msg.text.replace(/\*\*/g, '').replace(/\[.*?\]/g, '');
                    bodyText += `[${role}]: ${cleanText}\n\n`;
                });
            }

            const body = encodeURIComponent(bodyText);
            window.location.href = `mailto:RecordSystemservice@rba.gov.au?cc=casaoll@rba.gov.au&subject=${subject}&body=${body}`;

        } catch (err) {
            console.error("Summarization failed:", err);
            alert("Failed to generate summary, opening email with transcript only.");
        } finally {
            btn.textContent = originalText;
            btn.style.pointerEvents = 'auto';
            btn.style.cursor = 'pointer';
        }
    };

    if (emailSupportBtn) {
        emailSupportBtn.addEventListener('click', (e) => handleEmailSupport(e, emailSupportBtn));
    }

    const emailSupportFooter = document.getElementById('email-support-footer');
    if (emailSupportFooter) {
        emailSupportFooter.addEventListener('click', (e) => handleEmailSupport(e, emailSupportFooter));
    }
    userInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.value === '') this.style.height = 'auto';
    });

    // Handle Enter key
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);

    resetBtn.addEventListener('click', async () => {
        if (confirm('Are you sure you want to clear the chat history?')) {
            await fetch('/reset', { method: 'POST' });
            // Restore Welcome Screen
            messagesList.innerHTML = '';
            chatHistory = [];
            if (welcomeScreen) welcomeScreen.style.display = 'flex';
            closePdf();
        }
    });

    if (closePdfBtn) {
        closePdfBtn.addEventListener('click', closePdf);
    }

    // Global function for suggestion chips
    window.useSuggestion = function (text) {
        userInput.value = text;
        sendMessage();
    };

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text || isProcessing) return;

        // Hide welcome screen on first message
        if (welcomeScreen && welcomeScreen.style.display !== 'none') {
            welcomeScreen.style.display = 'none';
        }

        isProcessing = true;
        userInput.disabled = true;
        sendBtn.disabled = true;

        // Add user message
        addMessage(text, 'user');
        chatHistory.push({ role: 'User', text: text });
        userInput.value = '';
        userInput.style.height = 'auto';

        // Create a placeholder for the bot's response
        const botMsgDiv = document.createElement('div');
        botMsgDiv.className = 'message bot';

        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        const img = document.createElement('img');
        img.src = '/static/images/CM-Logo.png';
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.borderRadius = '50%';
        avatar.appendChild(img);

        const bubble = document.createElement('div');
        bubble.className = 'bubble';

        // --- Thought Process UI ---
        const thoughtDiv = document.createElement('div');
        thoughtDiv.className = 'thought-process';
        thoughtDiv.style.display = 'none'; // Hide initially until first log

        const thoughtHeader = document.createElement('div');
        thoughtHeader.className = 'thought-header';

        const thoughtIcon = document.createElement('span');
        thoughtIcon.className = 'thought-icon';
        thoughtIcon.textContent = '▶';

        const thoughtTitle = document.createElement('span');
        thoughtTitle.textContent = 'Thought for 0s';

        thoughtHeader.appendChild(thoughtIcon);
        thoughtHeader.appendChild(thoughtTitle);

        const thoughtContent = document.createElement('div');
        thoughtContent.className = 'thought-content';

        thoughtDiv.appendChild(thoughtHeader);
        thoughtDiv.appendChild(thoughtContent);

        // Toggle Logic
        thoughtHeader.addEventListener('click', () => {
            thoughtDiv.classList.toggle('open');
        });

        bubble.appendChild(thoughtDiv);
        // ---------------------------

        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'typing-indicator';
        typingIndicator.innerHTML = '<span></span><span></span><span></span>';
        bubble.appendChild(typingIndicator);

        botMsgDiv.appendChild(avatar);
        botMsgDiv.appendChild(bubble);
        messagesList.appendChild(botMsgDiv);
        scrollToBottom();

        let timerInterval;
        let startTime;

        try {
            const formData = new FormData();
            formData.append('user_input', text);

            const response = await fetch('/chat', {
                method: 'POST',
                body: formData
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let finalAnswer = '';
            let sources = [];
            let needsEmail = false;

            const answerTextDiv = document.createElement('div');
            bubble.appendChild(answerTextDiv);

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep incomplete line in buffer

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const event = JSON.parse(line);

                        if (event.type === 'log') {
                            // Start timer on first log if not started
                            if (!startTime) {
                                startTime = Date.now();
                                thoughtDiv.style.display = 'block'; // Show container
                                timerInterval = setInterval(() => {
                                    const elapsed = Math.floor((Date.now() - startTime) / 1000);
                                    thoughtTitle.textContent = `Thought for ${elapsed}s`;
                                }, 1000);
                            }

                            // Remove typing indicator when thinking starts
                            if (typingIndicator.parentNode) {
                                typingIndicator.remove();
                            }

                            const logItem = document.createElement('div');
                            logItem.className = 'thought-item';
                            logItem.textContent = event.content;
                            thoughtContent.appendChild(logItem);

                            // Auto-scroll thought content
                            thoughtContent.scrollTop = thoughtContent.scrollHeight;

                        } else if (event.type === 'answer') {
                            finalAnswer = event.content;
                            needsEmail = event.needs_email_support;
                            sources = event.sources || [];

                            // Stop timer
                            if (timerInterval) clearInterval(timerInterval);
                            if (startTime) {
                                const finalElapsed = Math.floor((Date.now() - startTime) / 1000);
                                thoughtTitle.textContent = `Thought for ${finalElapsed}s`;
                            }

                            // Remove typing indicator if it's still there
                            if (typingIndicator.parentNode) typingIndicator.remove();

                            // Render Markdown with RecordSystem links
                            const linkedAnswer = linkifyTrimRecords(finalAnswer);
                            answerTextDiv.innerHTML = marked.parse(linkedAnswer);

                            // Update history for email support
                            chatHistory.push({ role: 'Bot', text: finalAnswer });
                        } else if (event.type === 'error') {
                            answerTextDiv.innerHTML += `<br><span style="color:red">Error: ${event.content}</span>`;
                        }
                    } catch (e) {
                        console.error("Error parsing stream:", e);
                    }
                }
                scrollToBottom();
            }

            // Append sources if available (though Agent might not return structured ones)
            // Append sources if available (though Agent might not return structured ones)
            // if (sources && sources.length > 0) {
            //     const sourcesDiv = document.createElement('div');
            //     sourcesDiv.className = 'sources-list';
            //     sourcesDiv.innerHTML = '<strong>Sources:</strong>';
            //     sources.forEach(src => {
            //         const chip = document.createElement('div');
            //         chip.className = 'source-chip';
            //         chip.innerHTML = `📄 ${src.title}`;
            //         chip.onclick = () => openPdf(src.url, src.title);
            //         chip.style.cursor = 'pointer';
            //         sourcesDiv.appendChild(chip);
            //     });
            //     bubble.appendChild(sourcesDiv);
            // }

            // Append Action Buttons
            const messageId = Date.now().toString();
            const actionsDiv = createActionButtons(messageId, text, finalAnswer, sources);
            bubble.appendChild(actionsDiv);

            // Show email support if needed
            if (needsEmail) {
                emailSupportBtn.style.display = 'flex';
            }

        } catch (error) {
            console.error('Error:', error);
            bubble.innerHTML = 'Sorry, something went wrong. Please try again.';
        } finally {
            isProcessing = false;
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    }

    function addMessage(text, role, sources = [], needsEmail = false, originalQuery = '') {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        if (role === 'user') {
            avatar.textContent = '👤';
        } else {
            const img = document.createElement('img');
            img.src = '/static/images/CM-Logo.png';
            img.style.width = '100%';
            img.style.height = '100%';
            img.style.borderRadius = '50%';
            avatar.appendChild(img);
        }

        const bubble = document.createElement('div');
        bubble.className = 'bubble';

        // Simple markdown parsing for the text
        bubble.innerHTML = parseMarkdown(text);

        msgDiv.appendChild(avatar);
        msgDiv.appendChild(bubble);
        messagesList.appendChild(msgDiv);
        scrollToBottom();
        return msgDiv.id = 'msg-' + Date.now();
    }

    function removeMessage(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    function openPdf(url, title) {
        if (!url) {
            alert('No document URL available for this source.');
            return;
        }
        pdfTitle.textContent = title || 'Document Viewer';
        pdfFrame.src = url;
        pdfPanel.classList.add('open');
    }

    function closePdf() {
        pdfPanel.classList.remove('open');
        pdfFrame.src = '';
    }

    function linkifyTrimRecords(text) {
        if (!text) return '';
        // Regex to find D##/######
        const trimRegex = /\b(D\d{2}\/\d{6})\b/g;
        return text.replace(trimRegex, (match) => {
            // Replace / with %252f for the URL
            const encodedMatch = match.replace('/', '%252f');
            const url = `https://trimweb.rba.gov.au/easylink/?${encodedMatch}%3fdb%3dRC%26view`;
            return `[${match}](${url})`;
        });
    }

    function parseMarkdown(text) {
        if (!text) return '';

        // Linkify RecordSystem records before markdown parsing
        text = linkifyTrimRecords(text);

        // Use marked if available, otherwise fallback to simple parsing
        if (typeof marked !== 'undefined') {
            return marked.parse(text);
        }

        // Escape HTML
        let html = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Links
        html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>');
        // Newlines to br
        html = html.replace(/\n/g, '<br>');
        return html;
    }

    function createActionButtons(messageId, userQuery, botResponse, sources) {
        const container = document.createElement('div');
        container.className = 'message-actions';

        // Thumbs Up
        const upBtn = document.createElement('button');
        upBtn.className = 'action-btn';
        upBtn.innerHTML = '👍';
        upBtn.title = 'Good response';
        upBtn.onclick = () => sendFeedback(messageId, userQuery, botResponse, sources, 1, upBtn, downBtn);

        // Thumbs Down
        const downBtn = document.createElement('button');
        downBtn.className = 'action-btn';
        downBtn.innerHTML = '👎';
        downBtn.title = 'Bad response';
        downBtn.onclick = () => sendFeedback(messageId, userQuery, botResponse, sources, -1, downBtn, upBtn);

        // Copy
        const copyBtn = document.createElement('button');
        copyBtn.className = 'action-btn';
        copyBtn.innerHTML = '📋';
        copyBtn.title = 'Copy to clipboard';
        copyBtn.onclick = () => {
            navigator.clipboard.writeText(botResponse).then(() => {
                copyBtn.classList.add('copy-success');
                copyBtn.innerHTML = '✅';
                setTimeout(() => {
                    copyBtn.classList.remove('copy-success');
                    copyBtn.innerHTML = '📋';
                }, 2000);
            });
        };

        // Email Support (New)
        const emailBtn = document.createElement('button');
        emailBtn.className = 'action-btn';
        emailBtn.innerHTML = '📧';
        emailBtn.title = 'Email RecordSystem Service Desk';
        emailBtn.onclick = (e) => {
            // We need to access the handleEmailSupport function.
            // Since it's defined inside DOMContentLoaded, we might need to expose it or move it.
            // For now, let's assume we can move handleEmailSupport to window or duplicate logic.
            // Better approach: Trigger the existing hidden button or footer link if available,
            // or just call the logic directly if we refactor.
            // Let's refactor handleEmailSupport to be globally accessible or trigger the event.
            const footerBtn = document.getElementById('email-support-footer');
            if (footerBtn) footerBtn.click();
        };

        container.appendChild(upBtn);
        container.appendChild(downBtn);
        container.appendChild(copyBtn);
        container.appendChild(emailBtn);

        return container;
    }

    async function sendFeedback(messageId, userQuery, botResponse, sources, rating, btn, otherBtn) {
        // Toggle active state
        if (btn.classList.contains('active')) {
            btn.classList.remove('active');
            return;
        }

        // Confirmation
        const sentiment = rating === 1 ? "positive" : "negative";
        if (!confirm(`Are you sure you want to submit ${sentiment} feedback?`)) {
            return;
        }

        btn.classList.add('active');
        otherBtn.classList.remove('active');

        // Transform sources to use RecordSystem Web URLs if applicable
        const processedSources = sources.map(src => {
            // Priority 1: Use explicit RecordSystem ID extracted by backend
            if (src.trim_id) {
                const encodedId = src.trim_id.replace('/', '%252f');
                const trimUrl = `https://trimweb.rba.gov.au/easylink/?${encodedId}%3fdb%3dRC%26view`;
                return { ...src, url: trimUrl };
            }

            // Priority 2: Fallback to regex on title/url (legacy)
            const trimRegex = /\b(D\d{2}\/\d{6})\b/;
            const match = src.title.match(trimRegex) || (src.url && src.url.match(trimRegex));

            if (match) {
                const trimId = match[1];
                const encodedId = trimId.replace('/', '%252f');
                const trimUrl = `https://trimweb.rba.gov.au/easylink/?${encodedId}%3fdb%3dRC%26view`;
                return { ...src, url: trimUrl };
            }
            return src;
        });

        try {
            const response = await fetch('/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message_id: messageId,
                    user_query: userQuery,
                    bot_response: botResponse,
                    sources: processedSources,
                    rating: rating
                })
            });

            if (response.ok) {
                alert("Thank you for your feedback! This helps us improve AskRecordSystem.");
            }
        } catch (err) {
            console.error('Feedback failed:', err);
        }
    }
});
