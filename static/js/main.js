document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const resetBtn = document.getElementById('reset-btn');
    const exportBtn = document.getElementById('export-btn');
    const suggestionChips = document.querySelectorAll('.suggestion-chip');
    const topicLinks = document.querySelectorAll('.topics-nav a');
    const infoPanel = document.getElementById('info-panel');
    const closePanelBtn = document.getElementById('close-panel');
    const modal = document.getElementById('modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    const closeModalBtn = document.getElementById('close-modal');
    const downloadBtn = document.getElementById('download-btn');
    const shareBtn = document.getElementById('share-btn');
    const recentReports = document.getElementById('recent-reports');
    const recentDashboards = document.getElementById('recent-dashboards');
    
    // Socket.io connection
    const socket = io();
    
    // Auto-resize textarea
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        
        // Reset height if empty
        if (this.value === '') {
            this.style.height = 'auto';
        }
    });
    
    // Handle form submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = userInput.value.trim();
        
        if (message) {
            // Add user message to chat
            addMessageToChat('user', message);
            
            // Clear input
            userInput.value = '';
            userInput.style.height = 'auto';
            
            // Show loading indicator
            showLoadingIndicator();
            
            // Send message to server
            sendMessageToServer(message);
        }
    });
    
    // Handle suggestion chips
    suggestionChips.forEach(chip => {
        chip.addEventListener('click', function() {
            const text = this.getAttribute('data-text');
            userInput.value = text;
            userInput.focus();
        });
    });
    
    // Handle topic links
    topicLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const topic = this.getAttribute('data-topic');
            loadTopicInfo(topic);
        });
    });
    
    // Handle reset button
    resetBtn.addEventListener('click', function() {
        if (confirm('Are you sure you want to reset the conversation?')) {
            resetConversation();
        }
    });
    
    // Handle export button
    exportBtn.addEventListener('click', function() {
        exportConversation();
    });
    
    // Handle close panel button
    closePanelBtn.addEventListener('click', function() {
        infoPanel.style.display = 'none';
    });
    
    // Handle close modal button
    closeModalBtn.addEventListener('click', function() {
        closeModal();
    });
    
    // Handle download button
    downloadBtn.addEventListener('click', function() {
        downloadContent();
    });
    
    // Handle share button
    shareBtn.addEventListener('click', function() {
        shareContent();
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });
    
    // Functions
    
    // Add message to chat
    function addMessageToChat(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Check if content contains links to visualizations or reports
        const processedContent = processMessageContent(content);
        
        contentDiv.innerHTML = processedContent;
        messageDiv.appendChild(contentDiv);
        
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Process message content to handle special formatting and links
    function processMessageContent(content) {
        // Convert URLs to clickable links
        content = content.replace(
            /(https?:\/\/[^\s]+)/g, 
            '<a href="$1" target="_blank">$1</a>'
        );
        
        // Handle visualization and report links
        content = content.replace(
            /(\/visualizations\/[a-f0-9-]+\.html)/g,
            '<a href="$1" class="visualization-link" onclick="event.preventDefault(); openVisualization(\'$1\');">View Visualization</a>'
        );
        
        content = content.replace(
            /(\/reports\/[a-f0-9-]+\.html)/g,
            '<a href="$1" class="report-link" onclick="event.preventDefault(); openReport(\'$1\');">View Report</a>'
        );
        
        // Convert markdown-style formatting
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Convert newlines to <br>
        content = content.replace(/\n/g, '<br>');
        
        return content;
    }
    
    // Show loading indicator
    function showLoadingIndicator() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message assistant loading';
        loadingDiv.innerHTML = `
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Remove loading indicator
    function removeLoadingIndicator() {
        const loadingIndicator = document.querySelector('.loading');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
    }
    
    // Send message to server
    function sendMessageToServer(message) {
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading indicator
            removeLoadingIndicator();
            
            // Add assistant message to chat
            addMessageToChat('assistant', data.response);
            
            // Check if the response contains visualization or report links
            checkForSpecialContent(data.response);
        })
        .catch(error => {
            console.error('Error:', error);
            removeLoadingIndicator();
            addMessageToChat('assistant', 'Sorry, there was an error processing your request. Please try again.');
        });
    }
    
    // Check for special content in the response
    function checkForSpecialContent(response) {
        // Check for visualization links
        const visualizationMatch = response.match(/(\/visualizations\/[a-f0-9-]+\.html)/);
        if (visualizationMatch) {
            const visualizationUrl = visualizationMatch[1];
            addToRecentList(recentDashboards, 'Dashboard', visualizationUrl);
        }
        
        // Check for report links
        const reportMatch = response.match(/(\/reports\/[a-f0-9-]+\.html)/);
        if (reportMatch) {
            const reportUrl = reportMatch[1];
            addToRecentList(recentReports, 'Report', reportUrl);
        }
    }
    
    // Add item to recent list
    function addToRecentList(listElement, type, url) {
        const li = document.createElement('li');
        const date = new Date();
        const formattedDate = `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
        
        li.innerHTML = `<a href="#" onclick="event.preventDefault(); open${type}('${url}');">${type} (${formattedDate})</a>`;
        
        // Add to the beginning of the list
        if (listElement.firstChild) {
            listElement.insertBefore(li, listElement.firstChild);
        } else {
            listElement.appendChild(li);
        }
        
        // Limit the list to 5 items
        while (listElement.children.length > 5) {
            listElement.removeChild(listElement.lastChild);
        }
    }
    
    // Reset conversation
    function resetConversation() {
        fetch('/api/reset', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            // Clear chat messages
            chatMessages.innerHTML = '';
            
            // Add welcome message
            addMessageToChat('assistant', 'Hello! I\'m your Renewable Energy Consultant. I can provide information on various renewable energy technologies, help with cost analysis, environmental impact assessments, and more. I can also generate reports and dashboards based on data analysis. How can I assist you today?');
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
    
    // Export conversation
    function exportConversation() {
        fetch('/api/export')
        .then(response => response.json())
        .then(data => {
            // Create a blob with the conversation data
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            
            // Create a link to download the blob
            const a = document.createElement('a');
            a.href = url;
            a.download = `renewable-energy-conversation-${new Date().toISOString().slice(0, 10)}.json`;
            document.body.appendChild(a);
            a.click();
            
            // Clean up
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
    
    // Load topic information
    function loadTopicInfo(topic) {
        // Show the info panel
        infoPanel.style.display = 'flex';
        
        // Set loading state
        const panelContent = infoPanel.querySelector('.panel-content');
        panelContent.innerHTML = '<div class="loading-spinner"></div>';
        
        // Prepare the query based on the topic
        let query = '';
        switch (topic) {
            case 'solar':
                query = 'Tell me about solar energy technology, efficiency, and applications';
                break;
            case 'wind':
                query = 'Tell me about wind energy technology, efficiency, and applications';
                break;
            case 'hydro':
                query = 'Tell me about hydroelectric energy technology, efficiency, and applications';
                break;
            case 'geothermal':
                query = 'Tell me about geothermal energy technology, efficiency, and applications';
                break;
            case 'biomass':
                query = 'Tell me about biomass energy technology, efficiency, and applications';
                break;
            case 'policy':
                query = 'Tell me about renewable energy policies and regulations';
                break;
            case 'economics':
                query = 'Tell me about renewable energy economics and ROI calculations';
                break;
            case 'implementation':
                query = 'Tell me about renewable energy implementation best practices';
                break;
            default:
                query = 'Tell me about renewable energy';
        }
        
        // Send the query to the server
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: query, context: 'info_panel' })
        })
        .then(response => response.json())
        .then(data => {
            // Update the panel content
            panelContent.innerHTML = `
                <h2>${topic.charAt(0).toUpperCase() + topic.slice(1)} Energy</h2>
                <div class="info-content">
                    ${processMessageContent(data.response)}
                </div>
            `;
        })
        .catch(error => {
            console.error('Error:', error);
            panelContent.innerHTML = '<p>Sorry, there was an error loading the information. Please try again.</p>';
        });
    }
    
    // Open visualization
    window.openVisualization = function(url) {
        openModal('Visualization', url);
    };
    
    // Open report
    window.openReport = function(url) {
        openModal('Report', url);
    };
    
    // Open modal
    function openModal(type, url) {
        modalTitle.textContent = type;
        modalBody.innerHTML = `<iframe src="${url}" style="width: 100%; height: 600px; border: none;"></iframe>`;
        modal.classList.add('active');
        
        // Set the current content URL for download and share
        modal.setAttribute('data-content-url', url);
    }
    
    // Close modal
    function closeModal() {
        modal.classList.remove('active');
        modalBody.innerHTML = '';
    }
    
    // Download content
    function downloadContent() {
        const url = modal.getAttribute('data-content-url');
        if (url) {
            window.open(url, '_blank');
        }
    }
    
    // Share content
    function shareContent() {
        const url = window.location.origin + modal.getAttribute('data-content-url');
        
        if (navigator.share) {
            navigator.share({
                title: modalTitle.textContent,
                url: url
            })
            .catch(error => {
                console.error('Error sharing:', error);
                fallbackShare(url);
            });
        } else {
            fallbackShare(url);
        }
    }
    
    // Fallback share method
    function fallbackShare(url) {
        // Create a temporary input to copy the URL
        const input = document.createElement('input');
        input.value = url;
        document.body.appendChild(input);
        input.select();
        document.execCommand('copy');
        document.body.removeChild(input);
        
        alert('URL copied to clipboard!');
    }
}); 