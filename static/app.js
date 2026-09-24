document.addEventListener('DOMContentLoaded', () => {
    // Initialize Telegram WebApp SDK if available
    if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
    }

    // Elements
    const sidebar = document.getElementById('sidebar');
    const sidebarOpenBtn = document.getElementById('sidebarOpenBtn');
    const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');
    const navItems = document.querySelectorAll('.nav-item');

    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const themeIcon = document.getElementById('themeIcon');

    const uploadBtn = document.getElementById('uploadBtn');
    const fileInput = document.getElementById('fileInput');
    const uploadBanner = document.getElementById('uploadBanner');
    const uploadFilename = document.getElementById('uploadFilename');
    const uploadStatus = document.getElementById('uploadStatus');
    const uploadPercent = document.getElementById('uploadPercent');
    const progressIndicator = document.getElementById('progressIndicator');

    const searchInput = document.getElementById('searchInput');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    const refreshBtn = document.getElementById('refreshBtn');

    const currentCategoryTitle = document.getElementById('currentCategoryTitle');
    const itemsCounter = document.getElementById('itemsCounter');
    const trashControls = document.getElementById('trashControls');
    const emptyTrashBtn = document.getElementById('emptyTrashBtn');

    const sortBtn = document.getElementById('sortBtn');
    const sortMenu = document.getElementById('sortMenu');
    const sortLabel = document.getElementById('sortLabel');
    const sortOptions = document.querySelectorAll('.sort-option');

    const viewGridBtn = document.getElementById('viewGridBtn');
    const viewListBtn = document.getElementById('viewListBtn');
    const filesGrid = document.getElementById('filesGrid');
    const filesTableWrapper = document.getElementById('filesTableWrapper');
    const filesTableBody = document.getElementById('filesTableBody');

    const loadingState = document.getElementById('loadingState');
    const emptyState = document.getElementById('emptyState');
    const emptyTitle = document.getElementById('emptyTitle');
    const emptyDesc = document.getElementById('emptyDesc');
    const emptyIcon = document.getElementById('emptyIcon');

    const dropOverlay = document.getElementById('dropOverlay');

    const countAll = document.getElementById('countAll');
    const countTrash = document.getElementById('countTrash');
    const storageTotalFiles = document.getElementById('storageTotalFiles');
    const storageTotalSize = document.getElementById('storageTotalSize');

    // Preview Modal Elements
    const previewModal = document.getElementById('previewModal');
    const modalFilename = document.getElementById('modalFilename');
    const modalFileIcon = document.getElementById('modalFileIcon');
    const modalDownloadBtn = document.getElementById('modalDownloadBtn');
    const modalCloseBtn = document.getElementById('modalCloseBtn');
    const modalBody = document.getElementById('modalBody');
    const modalFileSize = document.getElementById('modalFileSize');
    const modalFileDate = document.getElementById('modalFileDate');
    const modalFileId = document.getElementById('modalFileId');

    const toast = document.getElementById('toast');
    const toastIcon = document.getElementById('toastIcon');
    const toastMessage = document.getElementById('toastMessage');

    // App State
    let currentCategory = 'all';
    let currentSearch = '';
    let currentSort = 'date-desc';
    let currentView = localStorage.getItem('tg_drive_view') || 'grid';
    let currentTheme = localStorage.getItem('tg_drive_theme') || 'ayu-dark';
    let filesData = [];
    let activePreviewFile = null;

    // Theme Management (Ayu Dark & Ayu Light)
    function applyTheme(theme) {
        currentTheme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('tg_drive_theme', theme);
        themeIcon.textContent = theme === 'ayu-dark' ? 'light_mode' : 'dark_mode';
    }

    themeToggleBtn.addEventListener('click', () => {
        applyTheme(currentTheme === 'ayu-dark' ? 'ayu-light' : 'ayu-dark');
    });
    applyTheme(currentTheme);

    // View Management (Grid & List)
    function setView(view) {
        currentView = view;
        localStorage.setItem('tg_drive_view', view);
        if (view === 'grid') {
            viewGridBtn.classList.add('active');
            viewListBtn.classList.remove('active');
            filesGrid.classList.remove('hidden');
            filesTableWrapper.classList.add('hidden');
        } else {
            viewListBtn.classList.add('active');
            viewGridBtn.classList.remove('active');
            filesTableWrapper.classList.remove('hidden');
            filesGrid.classList.add('hidden');
        }
    }

    viewGridBtn.addEventListener('click', () => setView('grid'));
    viewListBtn.addEventListener('click', () => setView('list'));
    setView(currentView);

    // Mobile Sidebar Drawer
    sidebarOpenBtn.addEventListener('click', () => sidebar.classList.add('open'));
    sidebarCloseBtn.addEventListener('click', () => sidebar.classList.remove('open'));

    // Category Navigation
    const categoryTitles = {
        all: 'Все файлы',
        images: 'Изображения',
        videos: 'Видео',
        archives: 'Архивы',
        documents: 'Документы',
        trash: 'Корзина'
    };

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            currentCategory = item.dataset.category;
            currentCategoryTitle.textContent = categoryTitles[currentCategory] || 'Файлы';
            
            if (currentCategory === 'trash') {
                trashControls.classList.remove('hidden');
            } else {
                trashControls.classList.add('hidden');
            }

            sidebar.classList.remove('open');
            loadFiles();
        });
    });

    // Sort Dropdown
    sortBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        sortMenu.classList.toggle('hidden');
    });

    document.addEventListener('click', () => sortMenu.classList.add('hidden'));

    sortOptions.forEach(opt => {
        opt.addEventListener('click', () => {
            sortOptions.forEach(o => o.classList.remove('active'));
            opt.classList.add('active');
            currentSort = opt.dataset.sort;
            sortLabel.textContent = opt.textContent;
            sortMenu.classList.add('hidden');
            renderFiles();
        });
    });

    // Search Input
    let searchTimer;
    searchInput.addEventListener('input', (e) => {
        const val = e.target.value.trim();
        clearSearchBtn.classList.toggle('hidden', val.length === 0);
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            currentSearch = val;
            loadFiles();
        }, 250);
    });

    clearSearchBtn.addEventListener('click', () => {
        searchInput.value = '';
        clearSearchBtn.classList.add('hidden');
        currentSearch = '';
        loadFiles();
    });

    refreshBtn.addEventListener('click', () => loadFiles());

    // Fetch Files from Backend
    async function loadFiles() {
        showLoading(true);
        try {
            const params = new URLSearchParams();
            if (currentSearch) params.append('search', currentSearch);
            params.append('category', currentCategory);

            const res = await fetch(`/api/files?${params.toString()}`);
            if (!res.ok) throw new Error('Не удалось получить список файлов');

            const data = await res.json();
            filesData = data.files || [];
            
            // Update counts in UI
            countAll.textContent = data.total_active || 0;
            countTrash.textContent = data.total_trash || 0;
            storageTotalFiles.textContent = `${data.total_active || 0} объектов`;

            renderFiles();
        } catch (err) {
            showToast(err.message, 'error');
            showLoading(false);
        }
    }

    // Render Files (Grid + List)
    function renderFiles() {
        showLoading(false);

        // Client-side sorting
        const sorted = [...filesData].sort((a, b) => {
            switch (currentSort) {
                case 'name-asc': return a.filename.localeCompare(b.filename);
                case 'name-desc': return b.filename.localeCompare(a.filename);
                case 'size-asc': return (a.file_size || 0) - (b.file_size || 0);
                case 'size-desc': return (b.file_size || 0) - (a.file_size || 0);
                case 'date-asc': return (a.id || 0) - (b.id || 0);
                case 'date-desc':
                default: return (b.id || 0) - (a.id || 0);
            }
        });

        itemsCounter.textContent = `${sorted.length} объектов`;

        // Calculate total size for category
        let sumBytes = sorted.reduce((acc, f) => acc + (f.file_size || 0), 0);
        storageTotalSize.textContent = formatBytes(sumBytes);

        if (sorted.length === 0) {
            filesGrid.innerHTML = '';
            filesTableBody.innerHTML = '';
            emptyState.classList.remove('hidden');

            if (currentCategory === 'trash') {
                emptyIcon.textContent = 'delete_outline';
                emptyTitle.textContent = 'Корзина пуста';
                emptyDesc.textContent = 'Удаленные файлы попадают сюда перед полным удалением';
            } else if (currentSearch) {
                emptyIcon.textContent = 'search_off';
                emptyTitle.textContent = 'Ничего не найдено';
                emptyDesc.textContent = `По запросу «${escapeHtml(currentSearch)}» ничего не нашлось`;
            } else {
                emptyIcon.textContent = 'folder_open';
                emptyTitle.textContent = 'Папка пуста';
                emptyDesc.textContent = 'Загрузите файлы кнопкой выше или перетащите их сюда';
            }
            return;
        }

        emptyState.classList.add('hidden');

        // Render Grid
        filesGrid.innerHTML = '';
        sorted.forEach(file => {
            const card = document.createElement('div');
            card.className = 'file-card';
            const iconName = getFileMaterialIcon(file.filename, file.category);
            const sizeStr = formatBytes(file.file_size);
            const dateStr = formatDate(file.created_at);

            let previewHtml = `<span class="material-symbols-rounded file-card-icon">${iconName}</span>`;
            if (file.category === 'images') {
                previewHtml = `<img src="/api/download/${file.id}" alt="${escapeHtml(file.filename)}" loading="lazy">`;
            }

            card.innerHTML = `
                <div class="file-card-preview" onclick="openPreview(${file.id})">
                    ${previewHtml}
                </div>
                <div class="file-card-body" onclick="openPreview(${file.id})">
                    <span class="file-card-name" title="${escapeHtml(file.filename)}">${escapeHtml(file.filename)}</span>
                    <div class="file-card-meta">
                        <span>${sizeStr}</span>
                        <span>${dateStr}</span>
                    </div>
                </div>
                <div class="file-card-actions">
                    ${getActionButtonsHtml(file)}
                </div>
            `;
            filesGrid.appendChild(card);
        });

        // Render List / Table
        filesTableBody.innerHTML = '';
        sorted.forEach(file => {
            const tr = document.createElement('tr');
            const iconName = getFileMaterialIcon(file.filename, file.category);
            const sizeStr = formatBytes(file.file_size);
            const dateStr = formatDate(file.created_at);

            tr.innerHTML = `
                <td onclick="openPreview(${file.id})">
                    <div class="table-file-cell">
                        <span class="material-symbols-rounded table-file-icon">${iconName}</span>
                        <span title="${escapeHtml(file.filename)}">${escapeHtml(file.filename)}</span>
                    </div>
                </td>
                <td onclick="openPreview(${file.id})">${sizeStr}</td>
                <td onclick="openPreview(${file.id})">${dateStr}</td>
                <td class="col-actions">
                    <div class="table-actions">
                        ${getActionButtonsHtml(file)}
                    </div>
                </td>
            `;
            filesTableBody.appendChild(tr);
        });
    }

    function getActionButtonsHtml(file) {
        if (currentCategory === 'trash') {
            return `
                <button class="icon-btn" title="Восстановить" onclick="restoreFile(${file.id}, event)">
                    <span class="material-symbols-rounded">restore</span>
                </button>
                <button class="icon-btn" title="Удалить навсегда" onclick="permanentDeleteFile(${file.id}, event)">
                    <span class="material-symbols-rounded">delete_forever</span>
                </button>
            `;
        }
        return `
            <button class="icon-btn" title="Скачать" onclick="downloadFile(${file.id}, event)">
                <span class="material-symbols-rounded">download</span>
            </button>
            <button class="icon-btn" title="В корзину" onclick="trashFile(${file.id}, event)">
                <span class="material-symbols-rounded">delete</span>
            </button>
        `;
    }

    // Universal Preview Modal Logic
    window.openPreview = async (fileId) => {
        const file = filesData.find(f => f.id === fileId);
        if (!file) return;

        activePreviewFile = file;
        modalFilename.textContent = file.filename;
        modalFileIcon.textContent = getFileMaterialIcon(file.filename, file.category);
        modalFileSize.textContent = formatBytes(file.file_size);
        modalFileDate.textContent = formatDate(file.created_at);
        modalFileId.textContent = `ID: ${file.id}`;

        const downloadUrl = `/api/download/${file.id}`;
        modalDownloadBtn.onclick = () => window.location.href = downloadUrl;

        modalBody.innerHTML = '<div class="ayu-spinner"></div>';
        previewModal.classList.remove('hidden');

        const cat = file.category;
        const ext = file.filename.split('.').pop().toLowerCase();

        // 1. Image Preview
        if (cat === 'images') {
            modalBody.innerHTML = `<img src="${downloadUrl}" alt="${escapeHtml(file.filename)}">`;
        }
        // 2. Video Preview
        else if (cat === 'videos') {
            modalBody.innerHTML = `
                <video controls autoplay playsinline>
                    <source src="${downloadUrl}" type="${file.mime_type || 'video/mp4'}">
                    Ваш браузер не поддерживает воспроизведение этого видео.
                </video>
            `;
        }
        // 3. Audio Preview
        else if (cat === 'audio') {
            modalBody.innerHTML = `
                <audio controls autoplay>
                    <source src="${downloadUrl}" type="${file.mime_type || 'audio/mpeg'}">
                    Ваш браузер не поддерживает аудио.
                </audio>
            `;
        }
        // 4. Archive (ZIP) Preview with JSZip
        else if (ext === 'zip' && window.JSZip) {
            modalBody.innerHTML = `
                <div class="state-container">
                    <div class="ayu-spinner"></div>
                    <p>Чтение структуры архива...</p>
                </div>
            `;
            try {
                const response = await fetch(downloadUrl);
                const blob = await response.blob();
                const zip = await JSZip.loadAsync(blob);
                
                let fileRows = '';
                let totalZipFiles = 0;

                zip.forEach((relativePath, zipEntry) => {
                    totalZipFiles++;
                    const isDir = zipEntry.dir;
                    const sizeStr = isDir ? '-' : formatBytes(zipEntry._data ? zipEntry._data.uncompressedSize : 0);
                    const icon = isDir ? 'folder' : 'draft';

                    fileRows += `
                        <tr>
                            <td>
                                <div class="archive-filename-cell">
                                    <span class="material-symbols-rounded">${icon}</span>
                                    <span>${escapeHtml(relativePath)}</span>
                                </div>
                            </td>
                            <td>${sizeStr}</td>
                        </tr>
                    `;
                });

                modalBody.innerHTML = `
                    <div class="archive-tree">
                        <table class="archive-table">
                            <thead>
                                <tr>
                                    <th>Имя файла (${totalZipFiles} элементов)</th>
                                    <th style="width: 110px;">Размер</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${fileRows || '<tr><td colspan="2">Архив пуст</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                `;
            } catch (err) {
                modalBody.innerHTML = `
                    <div class="state-container">
                        <span class="material-symbols-rounded empty-icon">folder_zip</span>
                        <h3>Не удалось открыть архив</h3>
                        <p>${escapeHtml(err.message)}</p>
                    </div>
                `;
            }
        }
        // 5. Default Fallback
        else {
            modalBody.innerHTML = `
                <div class="state-container">
                    <span class="material-symbols-rounded empty-icon">${getFileMaterialIcon(file.filename, file.category)}</span>
                    <h3>${escapeHtml(file.filename)}</h3>
                    <p>Предпросмотр недоступен для этого типа файлов (${ext.toUpperCase()})</p>
                    <button class="btn btn-primary" style="margin-top: 16px; width: auto;" onclick="window.location.href='${downloadUrl}'">
                        <span class="material-symbols-rounded">download</span>
                        <span>Скачать файл</span>
                    </button>
                </div>
            `;
        }
    };

    modalCloseBtn.addEventListener('click', closeModal);
    previewModal.addEventListener('click', (e) => {
        if (e.target === previewModal) closeModal();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !previewModal.classList.contains('hidden')) {
            closeModal();
        }
    });

    function closeModal() {
        previewModal.classList.add('hidden');
        modalBody.innerHTML = '';
        activePreviewFile = null;
    }

    // Actions
    window.downloadFile = (fileId, e) => {
        if (e) e.stopPropagation();
        window.location.href = `/api/download/${fileId}`;
    };

    window.trashFile = async (fileId, e) => {
        if (e) e.stopPropagation();
        try {
            const res = await fetch(`/api/trash/${fileId}`, { method: 'POST' });
            if (!res.ok) throw new Error('Не удалось переместить в корзину');
            showToast('Файл перемещен в корзину', 'info');
            loadFiles();
        } catch (err) {
            showToast(err.message, 'error');
        }
    };

    window.restoreFile = async (fileId, e) => {
        if (e) e.stopPropagation();
        try {
            const res = await fetch(`/api/trash/restore/${fileId}`, { method: 'POST' });
            if (!res.ok) throw new Error('Не удалось восстановить файл');
            showToast('Файл восстановлен из корзины', 'success');
            loadFiles();
        } catch (err) {
            showToast(err.message, 'error');
        }
    };

    window.permanentDeleteFile = async (fileId, e) => {
        if (e) e.stopPropagation();
        if (!confirm('Удалить этот файл навсегда из Telegram? Это действие нельзя отменить.')) return;
        try {
            const res = await fetch(`/api/files/${fileId}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Не удалось удалить файл');
            showToast('Файл навсегда удален', 'success');
            loadFiles();
        } catch (err) {
            showToast(err.message, 'error');
        }
    };

    emptyTrashBtn.addEventListener('click', async () => {
        if (!confirm('Очистить всю корзину? Все файлы в ней будут удалены из Telegram навсегда.')) return;
        try {
            const res = await fetch('/api/trash/empty', { method: 'POST' });
            if (!res.ok) throw new Error('Не удалось очистить корзину');
            showToast('Корзина успешно очищена', 'success');
            loadFiles();
        } catch (err) {
            showToast(err.message, 'error');
        }
    });

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

            uploadBanner.classList.remove('hidden');
            uploadFilename.textContent = file.name;
            uploadStatus.textContent = 'Отправка на сервер...';
            progressIndicator.style.width = '0%';
            uploadPercent.textContent = '0%';

            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    progressIndicator.style.width = percent + '%';
                    uploadPercent.textContent = percent + '%';
                    if (percent === 100) {
                        uploadStatus.textContent = 'Сохранение в Telegram-хранилище...';
                    }
                }
            };

            xhr.onload = () => {
                if (xhr.status === 200) {
                    showToast(`Файл «${file.name}» загружен`, 'success');
                    resolve();
                } else {
                    let errMsg = `Ошибка загрузки «${file.name}»`;
                    try {
                        const res = JSON.parse(xhr.responseText);
                        if (res.detail) errMsg = res.detail;
                    } catch(e) {}
                    showToast(errMsg, 'error');
                    reject();
                }
                setTimeout(() => uploadBanner.classList.add('hidden'), 1500);
            };

            xhr.onerror = () => {
                showToast(`Сетевая ошибка при загрузке «${file.name}»`, 'error');
                uploadBanner.classList.add('hidden');
                reject();
            };

            xhr.send(formData);
        });
    }

    // Drag & Drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => {
        document.body.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
        });
    });

    document.body.addEventListener('dragenter', () => dropOverlay.classList.remove('hidden'));
    dropOverlay.addEventListener('dragleave', () => dropOverlay.classList.add('hidden'));

    dropOverlay.addEventListener('drop', (e) => {
        dropOverlay.classList.add('hidden');
        if (e.dataTransfer.files.length > 0) {
            uploadFiles(e.dataTransfer.files);
        }
    });

    // Helper functions
    function showLoading(show) {
        loadingState.classList.toggle('hidden', !show);
        if (show) {
            emptyState.classList.add('hidden');
            filesGrid.classList.add('hidden');
            filesTableWrapper.classList.add('hidden');
        } else {
            setView(currentView);
        }
    }

    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 Б';
        const k = 1024;
        const sizes = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function formatDate(dateStr) {
        if (!dateStr) return '-';
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    }

    function getFileMaterialIcon(filename, category) {
        if (category === 'images') return 'image';
        if (category === 'videos') return 'movie';
        if (category === 'archives') return 'folder_zip';
        if (category === 'documents') return 'description';
        if (category === 'audio') return 'audio_file';
        
        const ext = filename.split('.').pop().toLowerCase();
        if (['code', 'js', 'py', 'html', 'css', 'ts', 'json', 'sh'].includes(ext)) return 'code';
        if (['pdf'].includes(ext)) return 'picture_as_pdf';
        return 'draft';
    }

    function escapeHtml(text) {
        if (!text) return '';
        return String(text).replace(/[&<>"']/g, (m) => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
        }[m]));
    }

    let toastTimeout;
    function showToast(message, type = 'info') {
        clearTimeout(toastTimeout);
        toastMessage.textContent = message;
        toast.className = `toast-card ${type}`;
        
        if (type === 'success') toastIcon.textContent = 'check_circle';
        else if (type === 'error') toastIcon.textContent = 'error';
        else toastIcon.textContent = 'info';

        toast.classList.remove('hidden');
        toastTimeout = setTimeout(() => toast.classList.add('hidden'), 3500);
    }

    // Initial load
    loadFiles();
});
