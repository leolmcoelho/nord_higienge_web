/** Items JavaScript */
document.addEventListener('DOMContentLoaded', () => {
    // Carregar itens ao carregar a página
    loadItems();
});

/**
 * Carrega lista de itens
 */
async function loadItems() {
    try {
        const items = await apiCall('/items?limit=100');
        console.log('Itens:', items);
        // Atualizar tabela com os dados recebidos
    } catch (error) {
        console.error('Erro ao carregar itens:', error);
        showToast('Erro ao carregar itens', 'error');
    }
}

/**
 * Filtra itens por status
 * @param {boolean} downloaded - Status de download
 */
async function filterByStatus(downloaded) {
    try {
        const items = await apiCall(`/items?downloaded=${downloaded}`);
        console.log('Itens filtrados:', items);
        // Atualizar tabela
    } catch (error) {
        console.error('Erro ao filtrar itens:', error);
        showToast('Erro ao filtrar itens', 'error');
    }
}

/**
 * Filtra itens por período
 * @param {string} dateFrom - Data inicial
 * @param {string} dateTo - Data final
 */
async function filterByDate(dateFrom, dateTo) {
    try {
        const items = await apiCall(`/items?date_from=${dateFrom}&date_to=${dateTo}`);
        console.log('Itens filtrados:', items);
        // Atualizar tabela
    } catch (error) {
        console.error('Erro ao filtrar itens:', error);
        showToast('Erro ao filtrar itens', 'error');
    }
}

// Exportar funções para uso global
window.loadItems = loadItems;
window.filterByStatus = filterByStatus;
window.filterByDate = filterByDate;
