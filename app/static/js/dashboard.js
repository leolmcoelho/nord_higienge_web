/** Dashboard JavaScript */
document.addEventListener('DOMContentLoaded', () => {
    // Inicializar form de extração
    const extractionForm = document.getElementById('extractionForm');
    if (extractionForm) {
        extractionForm.addEventListener('submit', handleExtractionSubmit);
    }
});

/**
 * Abre o modal de nova extração
 */
function startNewExtraction() {
    openModal('extractionModal');
}

/**
 * Fecha o modal de extração
 */
function closeExtractionModal() {
    closeModal('extractionModal');
}

/**
 * Manipula o envio do formulário de extração
 * @param {Event} event - Evento de submit
 */
async function handleExtractionSubmit(event) {
    event.preventDefault();

    const form = event.target;

    // Validação de campos obrigatórios
    const vortalUser = form.querySelector('#vortalUser').value.trim();
    const vortalPassword = form.querySelector('#vortalPassword').value.trim();
    const dateFrom = form.querySelector('#dateFrom').value;
    const dateTo = form.querySelector('#dateTo').value;

    if (!vortalUser) {
        showToast('Por favor, informe o usuário do Vortal', 'warning');
        form.querySelector('#vortalUser').focus();
        return;
    }

    if (!vortalPassword) {
        showToast('Por favor, informe a senha do Vortal', 'warning');
        form.querySelector('#vortalPassword').focus();
        return;
    }

    if (!dateFrom) {
        showToast('Por favor, selecione a data inicial', 'warning');
        form.querySelector('#dateFrom').focus();
        return;
    }

    if (!dateTo) {
        showToast('Por favor, selecione a data final', 'warning');
        form.querySelector('#dateTo').focus();
        return;
    }

    const formData = new FormData(form);
    const config = {
        vortal_user: vortalUser,
        vortal_password: vortalPassword,
        acingov_user: formData.get('acingov_user') || null,
        acingov_password: formData.get('acingov_password') || null,
        date_from: dateFrom,
        date_to: dateTo,
        headless: formData.get('headless') === 'on',
        use_word_boundaries: formData.get('use_word_boundaries') === 'on',
    };

    try {
        showToast('Iniciando extração...', 'info');

        const response = await apiCall('/jobs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        showToast('Extração iniciada com sucesso!', 'success');
        closeExtractionModal();

        // Redireciona para página de jobs
        if (response.job_uuid) {
            setTimeout(() => {
                window.location.href = `/jobs?uuid=${response.job_uuid}`;
            }, 1000);
        }
    } catch (error) {
        console.error('Erro ao iniciar extração:', error);
        showToast('Erro ao iniciar extração: ' + error.message, 'error');
    }
}

/**
 * Atualiza estatísticas do dashboard
 */
async function updateStats() {
    try {
        const stats = await apiCall('/jobs/stats');
        updateStatValue('total-jobs', stats.total_jobs);
        updateStatValue('active-jobs', stats.active_jobs);
        updateStatValue('downloads-today', stats.downloads_today);
        updateStatValue('success-rate', stats.success_rate + '%');
    } catch (error) {
        console.error('Erro ao atualizar estatísticas:', error);
    }
}

/**
 * Atualiza valor de um elemento de estatística
 * @param {string} id - ID do elemento
 * @param {string|number} value - Novo valor
 */
function updateStatValue(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

/**
 * Atualiza lista de jobs recentes
 */
async function updateRecentJobs() {
    try {
        const jobs = await apiCall('/jobs?limit=5');
        // Implementar atualização da tabela de jobs
        console.log('Jobs recentes:', jobs);
    } catch (error) {
        console.error('Erro ao atualizar jobs:', error);
    }
}

// Exportar funções para uso global
window.startNewExtraction = startNewExtraction;
window.closeExtractionModal = closeExtractionModal;
window.handleExtractionSubmit = handleExtractionSubmit;
window.updateStats = updateStats;
window.updateRecentJobs = updateRecentJobs;
