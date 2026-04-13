/**
 * 表格列拖拽功能 - 重构版
 * 使用列唯一标识而非列名，避免张冠李戴
 */

class ColumnDragger {
    constructor(tableId, storageKey) {
        this.table = document.getElementById(tableId);
        this.storageKey = storageKey;
        if (!this.table) return;

        this.init();
    }

    init() {
        const headerRow = this.table.querySelector('thead tr');
        if (!headerRow) return;

        // 给每个th分配唯一标识（基于列名，因为列名相对稳定）
        const ths = headerRow.querySelectorAll('th');
        ths.forEach((th, index) => {
            // 使用列名作为唯一标识（去掉特殊字符）
            const colName = th.textContent.trim().replace(/[^\w\u4e00-\u9fa5]/g, '_');
            th.setAttribute('data-col-name', colName);

            // checkbox列和sticky操作列不可拖拽
            if (th.querySelector('input[type="checkbox"]') || th.style.position === 'sticky') {
                th.setAttribute('data-draggable', 'false');
                return;
            }

            th.setAttribute('draggable', 'true');
            th.style.cursor = 'grab';

            th.addEventListener('dragstart', this.onDragStart.bind(this));
            th.addEventListener('dragover', this.onDragOver.bind(this));
            th.addEventListener('drop', this.onDrop.bind(this));
            th.addEventListener('dragend', this.onDragEnd.bind(this));
        });

        // 恢复保存的列顺序
        this.restoreColumnOrder();
    }

    onDragStart(e) {
        const th = e.target.closest('th');
        if (!th || th.getAttribute('draggable') !== 'true') return;

        this.draggedTh = th;
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', th.getAttribute('data-col-name'));

        setTimeout(() => {
            th.style.opacity = '0.5';
            th.style.backgroundColor = '#e0f2fe';
        }, 0);
    }

    onDragOver(e) {
        e.preventDefault();
        const th = e.target.closest('th');
        if (!th || th.getAttribute('draggable') !== 'true' || th === this.draggedTh) return;

        // 先清除所有列的边框，再给当前列添加边框
        this.table.querySelectorAll('thead th').forEach(t => t.style.borderLeft = '');
        th.style.borderLeft = '3px solid #3b82f6';
    }

    onDrop(e) {
        e.preventDefault();
        const targetTh = e.target.closest('th');
        if (!targetTh || targetTh.getAttribute('draggable') !== 'true' || targetTh === this.draggedTh) return;

        targetTh.style.borderLeft = '';

        // 获取两列的唯一标识
        const fromName = this.draggedTh.getAttribute('data-col-name');
        const toName = targetTh.getAttribute('data-col-name');

        // 交换列
        this.swapColumnsByName(fromName, toName);
        this.saveColumnOrder();
    }

    onDragEnd(e) {
        if (this.draggedTh) {
            this.draggedTh.style.opacity = '1';
            this.draggedTh.style.backgroundColor = '';
        }
        this.table.querySelectorAll('thead th').forEach(th => th.style.borderLeft = '');
        this.draggedTh = null;
    }

    swapColumnsByName(fromName, toName) {
        const headerRow = this.table.querySelector('thead tr');
        const tbody = this.table.querySelector('tbody');

        // 重新获取当前的表头列表（每次都重新获取，避免引用问题）
        const currentThs = Array.from(headerRow.querySelectorAll('th'));
        const fromIndex = currentThs.findIndex(th => th.getAttribute('data-col-name') === fromName);
        const toIndex = currentThs.findIndex(th => th.getAttribute('data-col-name') === toName);

        if (fromIndex === -1 || toIndex === -1) return;

        // 关键：先交换表体，再交换表头
        // 这样表体的索引计算基于原始顺序，不会受表头交换的影响

        // 交换表体每行的对应单元格
        const rows = tbody.querySelectorAll('tr');
        rows.forEach(row => {
            const cells = Array.from(row.querySelectorAll('td'));
            // 跳过 colspan 的行（如"暂无数据"行）
            if (cells.length === 1 && cells[0].hasAttribute('colspan')) return;

            if (cells.length > fromIndex && cells.length > toIndex) {
                const fromCell = cells[fromIndex];
                const toCell = cells[toIndex];

                if (fromCell && toCell) {
                    if (fromIndex < toIndex) {
                        toCell.parentNode.insertBefore(fromCell, toCell.nextSibling);
                    } else {
                        toCell.parentNode.insertBefore(fromCell, toCell);
                    }
                }
            }
        });

        // 最后交换表头
        const fromTh = currentThs[fromIndex];
        const toTh = currentThs[toIndex];

        if (fromIndex < toIndex) {
            toTh.parentNode.insertBefore(fromTh, toTh.nextSibling);
        } else {
            toTh.parentNode.insertBefore(fromTh, toTh);
        }
    }

    saveColumnOrder() {
        const headerRow = this.table.querySelector('thead tr');
        const ths = headerRow.querySelectorAll('th');
        // 只保存可拖拽列的顺序（用列名标识）
        const order = Array.from(ths)
            .filter(th => th.getAttribute('draggable') === 'true')
            .map(th => th.getAttribute('data-col-name'));
        localStorage.setItem(this.storageKey, JSON.stringify(order));
    }

    restoreColumnOrder() {
        const savedOrder = localStorage.getItem(this.storageKey);
        if (!savedOrder) return;

        try {
            const savedNames = JSON.parse(savedOrder);
            const headerRow = this.table.querySelector('thead tr');
            const tbody = this.table.querySelector('tbody');

            // 检查保存的顺序是否有效
            const currentThs = Array.from(headerRow.querySelectorAll('th'));
            const currentDraggable = currentThs.filter(th => th.getAttribute('draggable') === 'true');

            if (savedNames.length !== currentDraggable.length) {
                localStorage.removeItem(this.storageKey);
                return;
            }

            // 验证所有保存的列名是否都存在
            const allNamesExist = savedNames.every(name =>
                currentDraggable.some(th => th.getAttribute('data-col-name') === name)
            );
            if (!allNamesExist) {
                localStorage.removeItem(this.storageKey);
                return;
            }

            // 按保存的顺序逐个移动列
            for (let newPos = 0; newPos < savedNames.length; newPos++) {
                const targetName = savedNames[newPos];

                // 找到当前这个列在DOM中的实际位置
                const currentThsNow = Array.from(headerRow.querySelectorAll('th'));
                const currentPos = currentThsNow.findIndex(th => th.getAttribute('data-col-name') === targetName);

                // 同时找到目标位置的列是谁
                const targetPosTh = currentDraggable[newPos];
                const targetPosIndex = currentThsNow.indexOf(targetPosTh);

                if (currentPos !== targetPosIndex && currentPos !== -1) {
                    // 需要移动
                    const fromTh = currentThsNow[currentPos];
                    const toTh = currentThsNow[targetPosIndex];

                    // 先交换表体
                    const rows = tbody.querySelectorAll('tr');
                    rows.forEach(row => {
                        const cells = Array.from(row.querySelectorAll('td'));
                        if (cells.length === 1 && cells[0].hasAttribute('colspan')) return;

                        if (cells.length > currentPos && cells.length > targetPosIndex) {
                            const fromCell = cells[currentPos];
                            const toCell = cells[targetPosIndex];

                            if (fromCell && toCell) {
                                if (currentPos < targetPosIndex) {
                                    toCell.parentNode.insertBefore(fromCell, toCell.nextSibling);
                                } else {
                                    toCell.parentNode.insertBefore(fromCell, toCell);
                                }
                            }
                        }
                    });

                    // 再交换表头
                    if (currentPos < targetPosIndex) {
                        toTh.parentNode.insertBefore(fromTh, toTh.nextSibling);
                    } else {
                        toTh.parentNode.insertBefore(fromTh, toTh);
                    }
                }
            }

        } catch (e) {
            console.error('恢复列顺序失败:', e);
            localStorage.removeItem(this.storageKey);
        }
    }
}

function initColumnDragger(tableId, storageKey) {
    return new ColumnDragger(tableId, storageKey);
}