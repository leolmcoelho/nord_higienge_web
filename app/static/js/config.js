/** Config JavaScript */
document.addEventListener('DOMContentLoaded', () => {
    // Carregar palavras-chave ao carregar a página
    loadKeywords();
});

/**
 * Carrega lista de palavras-chave
 */
async function loadKeywords() {
    try {
        const keywords = await apiCall('/keywords');
        console.log('Keywords:', keywords);
        // Atualizar UI com as palavras-chave
        updateKeywordsUI(keywords);
    } catch (error) {
        console.error('Erro ao carregar keywords:', error);
        showToast('Erro ao carregar palavras-chave', 'error');
    }
}

/**
 * Adiciona uma nova palavra-chave
 */
async function addKeyword() {
    const input = document.getElementById('keywordInput');
    const word = input.value.trim();

    if (!word) {
        showToast('Por favor, digite uma palavra-chave', 'warning');
        return;
    }

    try {
        const keyword = await apiCall('/keywords', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ word })
        });

        showToast('Palavra-chave adicionada!', 'success');
        input.value = '';
        loadKeywords();
    } catch (error) {
        console.error('Erro ao adicionar keyword:', error);
        showToast('Erro ao adicionar palavra-chave: ' + error.message, 'error');
    }
}

/**
 * Faz upload de arquivo de palavras-chave
 */
async function uploadKeywords() {
    const fileInput = document.getElementById('keywordFile');
    const file = fileInput.files[0];

    if (!file) {
        showToast('Por favor, selecione um arquivo', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/keywords/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Erro no upload');
        }

        const result = await response.json();
        showToast(`${result.count} palavras-chave carregadas!`, 'success');
        loadKeywords();
        fileInput.value = '';
    } catch (error) {
        console.error('Erro ao fazer upload:', error);
        showToast('Erro ao fazer upload: ' + error.message, 'error');
    }
}

/**
 * Atualiza UI de palavras-chave
 * @param {Array} keywords - Lista de palavras-chave
 */
function updateKeywordsUI(keywords) {
    const container = document.querySelector('.keywords-list');
    if (!container) return;

    if (!keywords || keywords.length === 0) {
        container.innerHTML = '<p class="text-center">Nenhuma palavra-chave configurada</p>';
        return;
    }

    container.innerHTML = keywords.map(kw => `
        <div class="keyword-item">
            <span>${kw.word}</span>
            ${kw.source_file ? `<span class="keyword-source">${kw.source_file}</span>` : ''}
        </div>
    `).join('');
}

// Exportar funções para uso global
window.loadKeywords = loadKeywords;
window.addKeyword = addKeyword;
window.uploadKeywords = uploadKeywords;
