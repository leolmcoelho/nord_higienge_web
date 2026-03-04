/** Main application JavaScript */
document.addEventListener('DOMContentLoaded', () => {
    // Inicializar Socket.IO
    if (typeof socketManager !== 'undefined') {
        socketManager.connect();
    }

    // Inicializar navegação
    initNavigation();

    // Inicializar modais
    initModals();
});

/**
 * Inicializa navegação da aplicação
 */
function initNavigation() {
    // Menu mobile
    const menuToggle = document.querySelector('.menu-toggle');
    const navbarMenu = document.querySelector('.navbar-menu');

    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            navbarMenu.classList.toggle('active');
        });
    }
}

/**
 * Inicializa modais
 */
function initModals() {
    // Fechar modal ao clicar fora
    window.onclick = (event) => {
        if (event.target.classList.contains('modal')) {
            event.target.classList.remove('active');
        }
    };

    // Fechar com ESC
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            document.querySelectorAll('.modal.active').forEach(modal => {
                modal.classList.remove('active');
            });
        }
    });
}

/**
 * Abre um modal
 * @param {string} modalId - ID do modal
 */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

/**
 * Fecha um modal
 * @param {string} modalId - ID do modal
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId) || document.querySelector('.modal.active');
    if (modal) {
        modal.classList.remove('active');
    }
}

/**
 * Formata data para display
 * @param {string} dateString - Data em formato ISO
 * @returns {string} Data formatada
 */
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Formata duração em segundos para legível
 * @param {number} seconds - Duração em segundos
 * @returns {string} Duração formatada
 */
function formatDuration(seconds) {
    if (!seconds) return '-';

    if (seconds < 60) {
        return `${seconds.toFixed(1)}s`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}m ${secs}s`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    }
}

/**
 * Exibe uma notificação toast
 * @param {string} message - Mensagem
 * @param {string} type - Tipo: 'success', 'error', 'warning', 'info'
 */
function showToast(message, type = 'info') {
    // Cria elemento toast
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    // Adiciona ao DOM
    document.body.appendChild(toast);

    // Remove após 3 segundos
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

/**
 * Realiza chamada à API
 * @param {string} endpoint - Endpoint da API
 * @param {object} options - Opções do fetch
 * @returns {Promise} Resposta da API
 */
async function apiCall(endpoint, options = {}) {
    const url = `/api${endpoint}`;

    try {
        const response = await fetch(url, options);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Erro na chamada da API');
        }

        return await response.json();
    } catch (error) {
        console.error('Erro na API:', error);
        throw error;
    }
}

// Exportar funções para uso global
window.openModal = openModal;
window.closeModal = closeModal;
window.formatDate = formatDate;
window.formatDuration = formatDuration;
window.showToast = showToast;
window.apiCall = apiCall;
