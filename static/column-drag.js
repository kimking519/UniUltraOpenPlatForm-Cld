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

        // 给每个th分配固定ID（基于初始位置，不受后续拖拽影响）
        const ths = headerRow.querySelectorAll('th');
        let draggableIndex = 0;
        ths.forEach((th, index) => {
            // checkbox列和sticky操作列不可拖拽
            if (th.querySelector('input[type="checkbox"]') || th.style.position === 'sticky') {
                th.setAttribute('data-draggable', 'false');
                th.setAttribute('data-col-id', `fixed_${index}`);
                return;
            }

            // 给可拖拽列分配固定ID
            th.setAttribute('data-col-id', `drag_${draggableIndex}`);
            th.setAttribute('data-draggable', 'true');
            draggableIndex++;

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
        e.dataTransfer.setData('text/plain', th.getAttribute('data-col-id'));

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
        const fromId = this.draggedTh.getAttribute('data-col-id');
        const toId = targetTh.getAttribute('data-col-id');

        // 交换列
        this.swapColumnsById(fromId, toId);
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

    swapColumnsById(fromId, toId) {
        const headerRow = this.table.querySelector('thead tr');
        const tbody = this.table.querySelector('tbody');

        // 重新获取当前的表头列表（每次都重新获取，避免引用问题）
        const currentThs = Array.from(headerRow.querySelectorAll('th'));
        const fromIndex = currentThs.findIndex(th => th.getAttribute('data-col-id') === fromId);
        const toIndex = currentThs.findIndex(th => th.getAttribute('data-col-id') === toId);

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
        // 只保存可拖拽列的顺序（用固定ID标识）
        const order = Array.from(ths)
            .filter(th => th.getAttribute('draggable') === 'true')
            .map(th => th.getAttribute('data-col-id'));
        localStorage.setItem(this.storageKey, JSON.stringify(order));
        console.log('[Drag] Saved order:', order);
    }

    restoreColumnOrder() {
        const savedOrder = localStorage.getItem(this.storageKey);
        if (!savedOrder) return;

        try {
            const savedIds = JSON.parse(savedOrder);
            console.log('[Drag] Restoring order:', savedIds);

            const headerRow = this.table.querySelector('thead tr');
            const tbody = this.table.querySelector('tbody');

            // 获取所有列（包括不可拖拽的）
            const allThs = Array.from(headerRow.querySelectorAll('th'));
            const allDraggable = allThs.filter(th => th.getAttribute('draggable') === 'true');

            if (savedIds.length !== allDraggable.length) {
                console.log('[Drag] Order mismatch, clearing');
                localStorage.removeItem(this.storageKey);
                return;
            }

            // 按保存的顺序逐个移动列
            for (let newPos = 0; newPos < savedIds.length; newPos++) {
                const targetId = savedIds[newPos];

                // 每次重新获取当前DOM状态
                const currentThs = Array.from(headerRow.querySelectorAll('th'));
                const currentPos = currentThs.findIndex(th => th.getAttribute('data-col-id') === targetId);

                // 找到目标位置应该放哪个元素（按savedIds顺序，newPos位置）
                // 需要找到当前在newPos位置的draggable元素
                let actualTargetIndex = -1;
                let draggableCount = 0;
                currentThs.forEach((th, i) => {
                    if (th.getAttribute('draggable') === 'true') {
                        if (draggableCount === newPos) {
                            actualTargetIndex = i;
                        }
                        draggableCount++;
                    }
                });

                if (currentPos !== actualTargetIndex && currentPos !== -1 && actualTargetIndex !== -1) {
                    // 需要移动
                    const fromTh = currentThs[currentPos];
                    const toTh = currentThs[actualTargetIndex];

                    // 先交换表体
                    const rows = tbody.querySelectorAll('tr');
                    rows.forEach(row => {
                        const cells = Array.from(row.querySelectorAll('td'));
                        if (cells.length === 1 && cells[0].hasAttribute('colspan')) return;

                        if (cells.length > currentPos && cells.length > actualTargetIndex) {
                            const fromCell = cells[currentPos];
                            const toCell = cells[actualTargetIndex];

                            if (fromCell && toCell) {
                                if (currentPos < actualTargetIndex) {
                                    toCell.parentNode.insertBefore(fromCell, toCell.nextSibling);
                                } else {
                                    toCell.parentNode.insertBefore(fromCell, toCell);
                                }
                            }
                        }
                    });

                    // 再交换表头
                    if (currentPos < actualTargetIndex) {
                        toTh.parentNode.insertBefore(fromTh, toTh.nextSibling);
                    } else {
                        toTh.parentNode.insertBefore(fromTh, toTh);
                    }

                    console.log(`[Drag] Moved ${targetId} from ${currentPos} to ${actualTargetIndex}`);
                }
            }

            console.log('[Drag] Order restored successfully');

        } catch (e) {
            console.error('[Drag] Restore failed:', e);
            localStorage.removeItem(this.storageKey);
        }
    }
}

function initColumnDragger(tableId, storageKey) {
    return new ColumnDragger(tableId, storageKey);
}