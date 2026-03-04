/** Jobs JavaScript */
document.addEventListener('DOMContentLoaded', () => {
    // Obter UUID da URL se existir
    const urlParams = new URLSearchParams(window.location.search);
    const jobUuid = urlParams.get('uuid');

    if (jobUuid) {
        // Carregar detalhes de um job específico
        loadJobDetails(jobUuid);
    } else {
        // Carregar lista de todos os jobs
        loadJobs();
    }
});

/**
 * Carrega lista de jobs
 */
async function loadJobs() {
    try {
        const jobs = await apiCall('/jobs');
        console.log('Jobs:', jobs);
        // Atualizar tabela com os dados recebidos
    } catch (error) {
        console.error('Erro ao carregar jobs:', error);
        showToast('Erro ao carregar jobs', 'error');
    }
}

/**
 * Carrega detalhes de um job específico
 * @param {string} jobUuid - UUID do job
 */
async function loadJobDetails(jobUuid) {
    try {
        const job = await apiCall(`/jobs/${jobUuid}`);
        console.log('Job:', job);
        // Atualizar UI com os detalhes do job
        updateJobDetailsUI(job);

        // Carregar logs do job
        loadJobLogs(jobUuid);

        // Conectar ao Socket.IO para atualizações em tempo real
        if (typeof socketManager !== 'undefined') {
            socketManager.connect();
            socketManager.joinJob(jobUuid);

            // Configurar callbacks
            socketManager.onJobProgress((data) => {
                console.log('Progresso:', data);
                updateProgress(data);
            });

            socketManager.onJobCompleted((data) => {
                console.log('Job completado:', data);
                showToast('Job completado com sucesso!', 'success');
                // Recarregar detalhes
                loadJobDetails(jobUuid);
            });

            socketManager.onJobFailed((data) => {
                console.error('Job falhou:', data);
                showToast('Job falhou: ' + data.error, 'error');
                // Recarregar detalhes
                loadJobDetails(jobUuid);
            });
        }
    } catch (error) {
        console.error('Erro ao carregar job:', error);
        showToast('Erro ao carregar job', 'error');
    }
}

/**
 * Carrega logs de um job
 * @param {string} jobUuid - UUID do job
 */
async function loadJobLogs(jobUuid) {
    try {
        const logs = await apiCall(`/jobs/${jobUuid}/logs`);
        console.log('Logs:', logs);
        displayLogs(logs);
    } catch (error) {
        console.error('Erro ao carregar logs:', error);
    }
}

/**
 * Exibe logs no container
 * @param {Array} logs - Lista de logs
 */
function displayLogs(logs) {
    const logsContainer = document.getElementById('logsContainer');
    const logsSection = document.getElementById('logsSection');

    if (!logsContainer || !logsSection) return;

    if (!logs || logs.length === 0) {
        logsSection.style.display = 'none';
        return;
    }

    logsSection.style.display = 'block';
    logsContainer.innerHTML = '';

    logs.forEach(log => {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${log.level.toLowerCase()}`;

        const timestamp = document.createElement('span');
        timestamp.className = 'log-timestamp';
        timestamp.textContent = formatTimestamp(log.timestamp);

        const level = document.createElement('span');
        level.className = `log-level log-${log.level.toLowerCase()}`;
        level.textContent = log.level;

        const message = document.createElement('span');
        message.className = 'log-message';
        message.textContent = log.message;

        logEntry.appendChild(timestamp);
        logEntry.appendChild(level);
        logEntry.appendChild(message);

        logsContainer.appendChild(logEntry);
    });
}

/**
 * Adiciona um novo log à lista
 * @param {object} log - Log a adicionar
 */
function appendLog(log) {
    const logsContainer = document.getElementById('logsContainer');
    const logsSection = document.getElementById('logsSection');

    if (!logsContainer || !logsSection) return;

    logsSection.style.display = 'block';

    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${log.level.toLowerCase()}`;

    const timestamp = document.createElement('span');
    timestamp.className = 'log-timestamp';
    timestamp.textContent = formatTimestamp(new Date().toISOString());

    const level = document.createElement('span');
    level.className = `log-level log-${log.level.toLowerCase()}`;
    level.textContent = log.level;

    const message = document.createElement('span');
    message.className = 'log-message';
    message.textContent = log.message;

    logEntry.appendChild(timestamp);
    logEntry.appendChild(level);
    logEntry.appendChild(message);

    logsContainer.insertBefore(logEntry, logsContainer.firstChild);
}

/**
 * Formata timestamp para exibição
 * @param {string} timestamp - Timestamp em ISO format
 * @returns {string} Timestamp formatado
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

/**
 * Atualiza UI com detalhes do job
 * @param {object} job - Dados do job
 */
function updateJobDetailsUI(job) {
    const content = document.getElementById('jobDetailsContent');
    if (!content) return;

    content.innerHTML = `
        <div class="job-details-grid">
            <div class="detail-item">
                <label>Status:</label>
                <span class="status-badge status-${job.status}">${job.status}</span>
            </div>
            <div class="detail-item">
                <label>Criado em:</label>
                <span>${formatDate(job.created_at)}</span>
            </div>
            <div class="detail-item">
                <label>UUID:</label>
                <span class="uuid">${job.uuid}</span>
            </div>
            <div class="detail-item">
                <label>Links Totais:</label>
                <span>${job.links_total || 0}</span>
            </div>
            <div class="detail-item">
                <label>Processados:</label>
                <span>${job.processed || 0}</span>
            </div>
            <div class="detail-item">
                <label>Baixados:</label>
                <span>${job.downloaded || 0}</span>
            </div>
            ${job.execution_time ? `
            <div class="detail-item">
                <label>Duração:</label>
                <span>${formatDuration(job.execution_time)}</span>
            </div>
            ` : ''}
            ${job.error_message ? `
            <div class="detail-item">
                <label>Erro:</label>
                <span class="error-text">${job.error_message}</span>
            </div>
            ` : ''}
        </div>
    `;
}

/**
 * Cancela um job
 * @param {string} jobUuid - UUID do job
 */
async function cancelJob(jobUuid) {
    if (!confirm('Tem certeza que deseja cancelar este job?')) {
        return;
    }

    try {
        await apiCall(`/jobs/${jobUuid}/cancel`, {
            method: 'POST'
        });
        showToast('Job cancelado com sucesso!', 'success');
        // Recarregar lista ou detalhes
        loadJobs();
    } catch (error) {
        console.error('Erro ao cancelar job:', error);
        showToast('Erro ao cancelar job: ' + error.message, 'error');
    }
}

/**
 * Atualiza barra de progresso
 * @param {object} data - Dados de progresso
 */
function updateProgress(data) {
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    if (progressBar && data.progress !== undefined) {
        progressBar.style.width = `${data.progress}%`;
    }

    if (progressText && data.message) {
        progressText.textContent = data.message;
    }
}

/**
 * Atualiza status do job
 * @param {string} status - Novo status
 */
function updateJobStatus(status) {
    const statusElement = document.getElementById('job-status');
    if (statusElement) {
        statusElement.textContent = status;
        statusElement.className = `status-badge status-${status}`;
    }
}

/**
 * Filtra jobs por status
 * @param {string} status - Status para filtrar
 */
async function filterJobs(status) {
    try {
        const jobs = await apiCall(`/jobs?status=${status}`);
        console.log('Jobs filtrados:', jobs);
        // Atualizar tabela
    } catch (error) {
        console.error('Erro ao filtrar jobs:', error);
        showToast('Erro ao filtrar jobs', 'error');
    }
}

// Exportar funções para uso global
window.loadJobs = loadJobs;
window.loadJobDetails = loadJobDetails;
window.cancelJob = cancelJob;
window.updateProgress = updateProgress;
window.updateJobStatus = updateJobStatus;
window.filterJobs = filterJobs;
