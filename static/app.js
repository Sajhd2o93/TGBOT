document.addEventListener('DOMContentLoaded', () => {
    // Initialize Telegram WebApp if available
    if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
    }

    const uploadBtn = document.getElementById('uploadBtn');
    const fileInput = document.getElementById('fileInput');
    const refreshBtn = document.getElementById('refreshBtn');
    const searchInput = document.getElementById('searchInput');
    const filesList = document.getElementById('filesList');
    const filesTable = document.getElementById('filesTable');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const emptyState = document.getElementById('emptyState');
    const filesCount = document.getElementById('filesCount');
    const totalSize = document.getElementById('totalSize');
    const dropZone = document.getElementById('dropZone');
    
    const progressContainer = document.getElementById('uploadProgressContainer');
    const progressStatusText = document.getElementById('uploadStatusText');
    const progressPercent = document.getElementById('uploadPercent');
    const progressBarFill = document.getElementById('progressBarFill');

    let currentFiles = [];

    // Fetch and render files
    async function loadFiles(query = '') {
        showLoading(true);
        try {
            const url = query ? `/api/files?search=${encodeURIComponent(query)}` : '/api/files';
            const response = await fetch(url);
            if (!response.ok) throw new Error('Ошибка загрузки списка файлов');
            
            currentFiles = await response.json();
            renderFiles(currentFiles);
        } catch (err) {
            showToast(err.message, 'error');
        } finally {
            showLoading(false);
        }
    }

    function renderFiles(files) {
        filesList.innerHTML = '';
        if (files.length === 0) {
            filesTable.classList.add('hidden');
            emptyState.classList.remove('hidden');
            filesCount.textContent = '0 файлов';
            totalSize.textContent = '0 MB';
            return;
        }

        emptyState.classList.add('hidden');
        filesTable.classList.remove('hidden');

        let totalSizeBytes = 0;

        files.forEach(file => {
            totalSizeBytes += file.file_size;
            const tr = document.createElement('tr');
            
            const iconClass = getFileIcon(file.filename, file.mime_type);
            const formattedSize = formatBytes(file.file_size);
            const formattedDate = formatDate(file.created_at);

            tr.innerHTML = `
                <td>
                    <div class="file-name-cell">
                        <i class="${iconClass} file-icon"></i>
                        <span class="file-title">${escapeHtml(file.filename)}</span>
                    </div>
                </td>
                <td>${formattedSize}</td>
                <td>${formattedDate}</td>
                <td class="actions-col">
                    <button class="action-btn download" title="Скачать" onclick="downloadFile(${file.id})">
                        <i class="fa-solid fa-download"></i>
                    </button>
                    <button class="action-btn delete" title="Удалить" onclick="deleteFile(${file.id})">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            `;
            filesList.appendChild(tr);
        });

        filesCount.textContent = `${files.length} файлов`;
        totalSize.textContent = formatBytes(totalSizeBytes);
    }

    // Upload Handler
    uploadBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadFiles(e.target.files);
        }
    });

    async function uploadFiles(fileList) {
        for (let i = 0; i < fileList.length; i++) {
            const file = fileList[i];
            await uploadSingleFile(file);
        }
        fileInput.value = '';
        loadFiles();
    }

    function uploadSingleFile(file) {
        return new Promise((resolve, reject) => {
            const formData = new FormData();
            formData.append('file', file);

            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/upload', true);

            progressContainer.classList.remove('hidden');
            progressStatusText.textContent = `Загрузка: ${file.name}`;

            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    progressBarFill.style.width = percent + '%';
                    progressPercent.textContent = percent + '%';
                }
            };

            xhr.onload = () => {
                if (xhr.status === 200) {
                    showToast(`Файл "${file.name}" загружен!`, 'success');
                    resolve();
                } else {
                    showToast(`Ошибка загрузки "${file.name}"`, 'error');
                    reject();
                }
                setTimeout(() => progressContainer.classList.add('hidden'), 1000);
            };

            xhr.onerror = () => {
                showToast(`Сбой сети при загрузке "${file.name}"`, 'error');
                progressContainer.classList.add('hidden');
                reject();
            };

            xhr.send(formData);
        });
    }

    // Global action helpers
    window.downloadFile = (fileId) => {
        window.location.href = `/api/download/${fileId}`;
    };

    window.deleteFile = async (fileId) => {
        if (!confirm('Вы уверены, что хотите удалить этот файл?')) return;
        try {
            const res = await fetch(`/api/files/${fileId}`, { method: 'DELETE' });
            if (res.ok) {
                showToast('Файл успешно удален', 'success');
                loadFiles();
            } else {
                throw new Error('Не удалось удалить файл');
            }
        } catch (err) {
            showToast(err.message, 'error');
        }
    };

    // Drag & Drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        document.body.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        });
    });

    document.body.addEventListener('dragenter', () => dropZone.classList.remove('hidden'));
    dropZone.addEventListener('dragleave', () => dropZone.classList.add('hidden'));

    dropZone.addEventListener('drop', (e) => {
        dropZone.classList.add('hidden');
        if (e.dataTransfer.files.length > 0) {
            uploadFiles(e.dataTransfer.files);
        }
    });

    // Search input debounce
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => loadFiles(e.target.value.trim()), 300);
    });

    refreshBtn.addEventListener('click', () => loadFiles(searchInput.value.trim()));

    // Utility functions
    function showLoading(show) {
        if (show) {
            loadingSpinner.classList.remove('hidden');
            filesTable.classList.add('hidden');
            emptyState.classList.add('hidden');
        } else {
            loadingSpinner.classList.add('hidden');
        }
    }

    function formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function formatDate(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    function getFileIcon(filename, mime) {
        const ext = filename.split('.').pop().toLowerCase();
        if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext)) return 'fa-solid fa-file-image';
        if (['mp4', 'mkv', 'avi', 'mov', 'webm'].includes(ext)) return 'fa-solid fa-file-video';
        if (['mp3', 'wav', 'ogg', 'flac'].includes(ext)) return 'fa-solid fa-file-audio';
        if (['pdf'].includes(ext)) return 'fa-solid fa-file-pdf';
        if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) return 'fa-solid fa-file-zipper';
        if (['doc', 'docx', 'txt', 'md'].includes(ext)) return 'fa-solid fa-file-lines';
        return 'fa-solid fa-file';
    }

    function escapeHtml(text) {
        return text.replace(/[&<>"']/g, (m) => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
        }[m]));
    }

    function showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.classList.remove('hidden');
        setTimeout(() => toast.classList.add('hidden'), 3000);
    }

    // Initial load
    loadFiles();
});
