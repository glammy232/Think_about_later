// Общая логика для всех страниц: ripple-эффект, экран загрузки,
// диалоговое окно добавления дохода/расхода.

function addRipple(el, evt) {
  const rect = el.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height) * 1.6;
  const ripple = document.createElement('span');
  ripple.className = 'ripple';
  ripple.style.width = ripple.style.height = size + 'px';
  const x = (evt.clientX ?? rect.left + rect.width / 2) - rect.left - size / 2;
  const y = (evt.clientY ?? rect.top + rect.height / 2) - rect.top - size / 2;
  ripple.style.left = x + 'px';
  ripple.style.top = y + 'px';
  el.appendChild(ripple);
  ripple.addEventListener('animationend', () => ripple.remove());
}

/* ---------------- Категории и иконки для новых операций ---------------- */
const CATEGORY_OPTIONS = {
  expense: ['Продукты', 'Коммуналка', 'Транспорт', 'Кафе и рестораны', 'Другое'],
  income: ['Зарплата', 'Перевод', 'Возврат долга', 'Другое'],
};

const CATEGORY_ICON = {
  'Продукты': { bg: '#fdeee2', color: '#e08a3c', path: '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.7 13.4a2 2 0 002 1.6h9.7a2 2 0 002-1.6L23 6H6"/>' },
  'Коммуналка': { bg: '#e7f0fb', color: '#4ea3e8', path: '<path d="M13 2L3 14h7l-1 8 10-12h-7z"/>' },
  'Транспорт': { bg: '#fdeee2', color: '#e08a3c', path: '<path d="M5 17h14M5 17a2 2 0 01-2-2v-3l2-5h14l2 5v3a2 2 0 01-2 2M5 17v2a1 1 0 001 1h1a1 1 0 001-1v-2m8 0v2a1 1 0 001 1h1a1 1 0 001-1v-2"/>' },
  'Кафе и рестораны': { bg: '#f2e9fb', color: '#9a5fd1', path: '<path d="M18 8h1a4 4 0 010 8h-1"/><path d="M2 8h16v9a4 4 0 01-4 4H6a4 4 0 01-4-4z"/><path d="M6 1v3M10 1v3M14 1v3"/>' },
  'Зарплата': { bg: '#e7f5ee', color: '#1a7a4c', path: '<path d="M12 1v22"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>' },
  'Перевод': { bg: '#e7f0fb', color: '#4ea3e8', path: '<path d="M17 3l4 4-4 4"/><path d="M21 7H9"/><path d="M7 21l-4-4 4-4"/><path d="M3 17h12"/>' },
  'Возврат долга': { bg: '#e7f5ee', color: '#1a7a4c', path: '<path d="M20 6L9 17l-5-5"/>' },
  'default': { bg: '#f1f4f2', color: '#5b665f', path: '<path d="M20.6 12.9a1 1 0 000-1.8L4.5 3.1a1 1 0 00-1.4 1.2L5.5 12l-2.4 7.7a1 1 0 001.4 1.2z"/>' },
};

let currentModalType = 'expense';

function fillCategoryOptions(select, type) {
  if (!select) return;
  select.innerHTML = '';
  CATEGORY_OPTIONS[type].forEach((cat) => {
    const opt = document.createElement('option');
    opt.value = cat;
    opt.textContent = cat;
    select.appendChild(opt);
  });
}

function openModal(type) {
  const overlay = document.getElementById('modal-overlay');
  if (!overlay) return;
  currentModalType = type === 'income' ? 'income' : 'expense';

  overlay.querySelectorAll('.type-toggle button').forEach((b) => b.classList.remove('active'));
  const activeBtn = overlay.querySelector('.type-toggle button[data-type="' + currentModalType + '"]');
  if (activeBtn) activeBtn.classList.add('active');

  fillCategoryOptions(document.getElementById('modal-category'), currentModalType);

  const title = document.getElementById('modal-title');
  if (title) title.textContent = currentModalType === 'expense' ? 'Новый расход' : 'Новый доход';

  const dateInput = document.getElementById('modal-date');
  if (dateInput) dateInput.valueAsDate = new Date();

  overlay.classList.add('open');
  setTimeout(() => {
    const amountEl = document.getElementById('modal-amount');
    if (amountEl) amountEl.focus();
  }, 150);
}

function closeModal() {
  const overlay = document.getElementById('modal-overlay');
  if (overlay) overlay.classList.remove('open');
  const form = document.getElementById('modal-form');
  if (form) form.reset();
}

function showToast(text) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = text;
  toast.classList.add('show');
  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => toast.classList.remove('show'), 2600);
}

function buildTxRowHTML(data) {
  const icon = CATEGORY_ICON[data.sub] || CATEGORY_ICON.default;
  const amtClass = data.income ? 'tx-amount income' : 'tx-amount';
  const sign = data.income ? '+' : '';
  return '<div class="tx-row" style="animation:fadeUp .3s ease;">' +
    '<div class="tx-icon" style="background:' + icon.bg + ';"><svg viewBox="0 0 24 24" fill="none" stroke="' + icon.color + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + icon.path + '</svg></div>' +
    '<div class="tx-info"><b>' + data.title + '</b><span>' + data.sub + '</span></div>' +
    '<div class="' + amtClass + '">' + sign + data.amount + ' ₽</div>' +
    '<div class="tx-who">' + data.who + '</div>' +
    '<div class="tx-date">' + data.date + '</div>' +
    '</div>';
}

function buildTableRowHTML(data) {
  const icon = CATEGORY_ICON[data.sub] || CATEGORY_ICON.default;
  const sign = data.income ? '+' : '';
  return '<tr style="animation:fadeUp .3s ease;">' +
    '<td><div style="display:flex; align-items:center; gap:12px;">' +
    '<div class="tx-icon" style="background:' + icon.bg + ';"><svg viewBox="0 0 24 24" fill="none" stroke="' + icon.color + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + icon.path + '</svg></div>' +
    '<div class="tx-info"><b>' + data.title + '</b><span>' + data.sub + '</span></div>' +
    '</div></td>' +
    '<td>' + data.who + '</td>' +
    '<td><span class="tx-tag">' + data.sub + '</span></td>' +
    '<td>' + data.date + '</td>' +
    '<td style="text-align:right;"><b style="' + (data.income ? 'color:var(--green)' : '') + '">' + sign + data.amount + ' ₽</b></td>' +
    '</tr>';
}

/* ---------------- Модалка «Долг» ---------------- */
let currentDebtDir = 'in';
const ARROW_DOWN_PATH = '<path d="M12 5v14M19 12l-7 7-7-7"/>';
const ARROW_UP_PATH = '<path d="M12 19V5M5 12l7-7 7 7"/>';

function openDebtModal(dir) {
  const overlay = document.getElementById('debt-modal-overlay');
  if (!overlay) return;
  currentDebtDir = dir === 'out' ? 'out' : 'in';

  overlay.querySelectorAll('.type-toggle button').forEach((b) => b.classList.remove('active'));
  const activeBtn = overlay.querySelector('.type-toggle button[data-dir="' + currentDebtDir + '"]');
  if (activeBtn) activeBtn.classList.add('active');

  const label = document.getElementById('debt-who-label');
  if (label) label.textContent = currentDebtDir === 'in' ? 'Кто вам должен' : 'Кому вы должны';

  const dateInput = document.getElementById('debt-date');
  if (dateInput) dateInput.valueAsDate = new Date();

  overlay.classList.add('open');
  setTimeout(() => {
    const amountEl = document.getElementById('debt-amount');
    if (amountEl) amountEl.focus();
  }, 150);
}

function closeDebtModal() {
  const overlay = document.getElementById('debt-modal-overlay');
  if (overlay) overlay.classList.remove('open');
  const form = document.getElementById('debt-form');
  if (form) form.reset();
}

function buildDebtCardHTML(data) {
  const dirClass = data.dir === 'in' ? 'in' : 'out';
  const arrowPath = data.dir === 'in' ? ARROW_DOWN_PATH : ARROW_UP_PATH;
  const sign = data.dir === 'in' ? '+' : '−';
  const heading = data.dir === 'in'
    ? (data.who + ' должен вам')
    : ('Вы должны ' + data.who);
  const actionBtn = data.dir === 'in'
    ? '<button class="ghost-btn" data-clickable>Напомнить</button>'
    : '<button class="primary-btn" data-clickable><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg> Оплатить</button>';

  return '<div class="debt-card ' + dirClass + '" style="animation:fadeUp .3s ease;">' +
    '<div class="dir"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + arrowPath + '</svg></div>' +
    '<div class="info"><b>' + heading + '</b><span>' + (data.comment || 'Без комментария') + '</span></div>' +
    '<div class="amt">' + sign + data.amount + ' ₽</div>' +
    actionBtn +
    '</div>';
}

document.addEventListener('DOMContentLoaded', () => {
  /* ---- экран загрузки ---- */
  const loader = document.getElementById('loader');
  if (loader) {
    const hide = () => setTimeout(() => loader.classList.add('hidden'), 500);
    if (document.readyState === 'complete') hide();
    else window.addEventListener('load', hide);
  }

  /* ---- ripple + анимация пункта меню ---- */
  document.querySelectorAll('[data-clickable]').forEach((el) => {
    const computedPosition = getComputedStyle(el).position;
    if (computedPosition === 'static') el.style.position = 'relative';
    if (!el.style.overflow) el.style.overflow = 'hidden';

    el.addEventListener('click', (e) => {
      addRipple(el, e);
      if (el.classList.contains('nav-item')) {
        el.classList.remove('pulse');
        void el.offsetWidth;
        el.classList.add('pulse');
      }
    });
  });

  /* ---- переключатели в настройках ---- */
  document.querySelectorAll('.switch input').forEach((input) => {
    input.addEventListener('change', () => {
      const row = input.closest('.settings-row');
      if (row) row.classList.toggle('is-on', input.checked);
    });
  });

  /* ---- модальное окно: добавить доход/расход ---- */
  document.querySelectorAll('[data-open-modal]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      openModal(btn.getAttribute('data-open-modal'));
    });
  });

  const overlayEl = document.getElementById('modal-overlay');
  if (overlayEl) {
    overlayEl.addEventListener('click', (e) => {
      if (e.target.id === 'modal-overlay') closeModal();
    });
  }
  const closeBtn = document.getElementById('modal-close');
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  const cancelBtn = document.getElementById('modal-cancel');
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeModal();
      closeDebtModal();
    }
  });

  document.querySelectorAll('.type-toggle button').forEach((btn) => {
    btn.addEventListener('click', () => openModal(btn.getAttribute('data-type')));
  });

  const modalForm = document.getElementById('modal-form');
  if (modalForm) {
    modalForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const amountInput = document.getElementById('modal-amount');
      const amount = Number((amountInput && amountInput.value) || 0);
      if (!amount || amount <= 0) {
        if (amountInput) amountInput.focus();
        return;
      }
      const categoryEl = document.getElementById('modal-category');
      const whoEl = document.getElementById('modal-who');
      const commentEl = document.getElementById('modal-comment');
      const category = (categoryEl && categoryEl.value) || 'Другое';
      const who = (whoEl && whoEl.value) || 'Вы';
      const comment = commentEl ? commentEl.value.trim() : '';
      const income = currentModalType === 'income';
      const title = comment || category;
      const formattedAmount = amount.toLocaleString('ru-RU');

      const data = { title: title, sub: category, amount: formattedAmount, who: who, date: 'Сегодня', income: income };

      const list = document.getElementById('tx-list');
      if (list) list.insertAdjacentHTML('afterbegin', buildTxRowHTML(data));

      const tbody = document.getElementById('tx-table-body');
      if (tbody) tbody.insertAdjacentHTML('afterbegin', buildTableRowHTML(data));

      closeModal();
      showToast(income ? 'Доход добавлен' : 'Расход добавлен');
    });
  }

  /* ---- модальное окно: добавить долг ---- */
  document.querySelectorAll('[data-open-debt-modal]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      openDebtModal(btn.getAttribute('data-open-debt-modal') || 'in');
    });
  });

  const debtOverlayEl = document.getElementById('debt-modal-overlay');
  if (debtOverlayEl) {
    debtOverlayEl.addEventListener('click', (e) => {
      if (e.target.id === 'debt-modal-overlay') closeDebtModal();
    });
    debtOverlayEl.querySelectorAll('.type-toggle button').forEach((btn) => {
      btn.addEventListener('click', () => openDebtModal(btn.getAttribute('data-dir')));
    });
  }
  const debtCloseBtn = document.getElementById('debt-modal-close');
  if (debtCloseBtn) debtCloseBtn.addEventListener('click', closeDebtModal);
  const debtCancelBtn = document.getElementById('debt-modal-cancel');
  if (debtCancelBtn) debtCancelBtn.addEventListener('click', closeDebtModal);

  const debtForm = document.getElementById('debt-form');
  if (debtForm) {
    debtForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const amountInput = document.getElementById('debt-amount');
      const amount = Number((amountInput && amountInput.value) || 0);
      if (!amount || amount <= 0) {
        if (amountInput) amountInput.focus();
        return;
      }
      const whoEl = document.getElementById('debt-who');
      const commentEl = document.getElementById('debt-comment');
      const who = (whoEl && whoEl.value) || 'Алексей';
      const comment = commentEl ? commentEl.value.trim() : '';
      const formattedAmount = amount.toLocaleString('ru-RU');

      const data = { dir: currentDebtDir, who: who, comment: comment, amount: formattedAmount };

      const list = document.getElementById('debt-list');
      if (list) list.insertAdjacentHTML('afterbegin', buildDebtCardHTML(data));

      closeDebtModal();
      showToast('Долг добавлен');

      // повторно навешиваем ripple на только что вставленные кнопки
      if (list) {
        list.querySelectorAll('[data-clickable]').forEach((el) => {
          if (el.dataset.rippleBound) return;
          el.dataset.rippleBound = '1';
          const pos = getComputedStyle(el).position;
          if (pos === 'static') el.style.position = 'relative';
          if (!el.style.overflow) el.style.overflow = 'hidden';
          el.addEventListener('click', (ev) => addRipple(el, ev));
        });
      }
    });
  }
});
