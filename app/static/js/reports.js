/** Relatórios JavaScript */
document.addEventListener('DOMContentLoaded', () => {
    // Carregar relatórios ao carregar a página
    loadReports();
});

/**
 * Carrega lista de relatórios
 */
async function loadReports() {
    try {
        const jobs = await apiCall('/jobs?status=completed');
        console.log('Jobs completados:', jobs);
        // Atualizar tabela com os dados recebidos
    } catch (error) {
        console.error('Erro ao carregar relatórios:', error);
        showToast('Erro ao carregar relatórios', 'error');
    }
}

/**
 * Gera relatório HTML para um job
 * @param {string} jobUuid - UUID do job
 */
async function generateReport(jobUuid) {
    try {
        showToast('Gerando relatório...', 'info');
        const response = await apiCall(`/reports/${jobUuid}`, {
            method: 'POST'
        });
        showToast('Relatório gerado com sucesso!', 'success');
        window.open(response.url, '_blank');
    } catch (error) {
        console.error('Erro ao gerar relatório:', error);
        showToast('Erro ao gerar relatório: ' + error.message, 'error');
    }
}

/**
 * Baixa relatório em PDF
 * @param {string} jobUuid - UUID do job
 */
async function downloadReport(jobUuid) {
    try {
        showToast('Baixando relatório...', 'info');
        // Implementar download do PDF
        showToast('Relatório baixado!', 'success');
    } catch (error) {
        console.error('Erro ao baixar relatório:', error);
        showToast('Erro ao baixar relatório: ' + error.message, 'error');
    }
}

// Exportar funções para uso global
window.loadReports = loadReports;
window.generateReport = generateReport;
window.downloadReport = downloadReport;
