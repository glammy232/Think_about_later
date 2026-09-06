/* Backend integration for the static hackathon UI. */
(() => {
  const API = '/api';
  const GROUP_ID = 'group-1';
  const USER_ID = localStorage.getItem('krug_user_id') || 'user-1';
  const state = { members: [], group: null };

  const escapeHtml = (value) => String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');
  const money = (value) => `${Number(value || 0).toLocaleString('ru-RU', { maximumFractionDigits: 2 })} ₽`;
  const formatDate = (value) => new Date(`${value}T00:00:00`).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
  const memberName = (id) => state.members.find((member) => member.id === id)?.name || id;
  const currentMember = () => state.members.find((member) => member.id === USER_ID);

  async function request(path, options = {}) {
    const response = await fetch(`${API}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-User-Id': USER_ID,
        ...(options.headers || {}),
      },
    });
    if (!response.ok) {
      let detail = `Ошибка ${response.status}`;
      try {
        const body = await response.json();
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      } catch (_) { /* keep status */ }
      throw new Error(detail);
    }
    return response.status === 204 ? null : response.json();
  }

  function notify(text, error = false) {
    if (typeof window.showToast === 'function') window.showToast(text);
    else window.alert(text);
    if (error) console.error(text);
  }

  function iconFor(category) {
    if (typeof window.CATEGORY_ICON !== 'undefined') {
      return window.CATEGORY_ICON[category] || window.CATEGORY_ICON.default;
    }
    return { bg: '#e7f5ee', color: '#1a7a4c', path: '<circle cx="12" cy="12" r="8"/>' };
  }

  async function loadContext() {
    [state.group, state.members] = await Promise.all([
      request(`/groups/${GROUP_ID}`),
      request(`/groups/${GROUP_ID}/members`),
    ]);
    document.querySelectorAll('.household .info').forEach((info) => {
      const title = info.querySelector('b');
      const subtitle = info.querySelector('span');
      if (title) title.childNodes[0].textContent = `${state.group.name} `;
      if (subtitle) subtitle.textContent = `${state.members.length} участников`;
    });
    document.querySelectorAll('.user-chip').forEach((chip) => {
      const avatar = chip.querySelector('.av');
      chip.childNodes.forEach((node) => {
        if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
          node.textContent = ` ${currentMember()?.name || 'Пользователь'} `;
        }
      });
      if (avatar && currentMember()?.avatar_url) {
        avatar.innerHTML = `<img alt="" src="${escapeHtml(currentMember().avatar_url)}" style="width:100%;height:100%;border-radius:50%;object-fit:cover">`;
      }
    });
    populateMemberSelects();
  }

  function populateMemberSelects() {
    ['modal-who', 'debt-who'].forEach((id) => {
      const select = document.getElementById(id);
      if (!select) return;
      select.innerHTML = state.members.map((member) =>
        `<option value="${escapeHtml(member.id)}">${escapeHtml(member.name)}</option>`).join('');
      select.value = id === 'modal-who' ? USER_ID : state.members.find((m) => m.id !== USER_ID)?.id;
    });
  }

  function operationData(operation) {
    return {
      title: operation.title,
      sub: operation.category,
      amount: Number(operation.amount).toLocaleString('ru-RU'),
      who: memberName(operation.payer_id),
      date: formatDate(operation.operation_date),
      income: operation.type === 'income',
    };
  }

  function operationRow(operation) {
    const data = operationData(operation);
    const icon = iconFor(data.sub);
    return `<div class="tx-row">
      <div class="tx-icon" style="background:${icon.bg}"><svg viewBox="0 0 24 24" fill="none" stroke="${icon.color}" stroke-width="2">${icon.path}</svg></div>
      <div class="tx-info"><b>${escapeHtml(data.title)}</b><span>${escapeHtml(data.sub)}</span></div>
      <div class="tx-amount ${data.income ? 'income' : ''}">${data.income ? '+' : ''}${money(operation.amount)}</div>
      <div class="tx-who">${escapeHtml(data.who)}</div><div class="tx-date">${data.date}</div>
    </div>`;
  }

  function operationTableRow(operation) {
    const data = operationData(operation);
    const icon = iconFor(data.sub);
    return `<tr><td><div style="display:flex;align-items:center;gap:12px">
      <div class="tx-icon" style="background:${icon.bg}"><svg viewBox="0 0 24 24" fill="none" stroke="${icon.color}" stroke-width="2">${icon.path}</svg></div>
      <div class="tx-info"><b>${escapeHtml(data.title)}</b><span>${escapeHtml(operation.comment || data.sub)}</span></div>
      </div></td><td>${escapeHtml(data.who)}</td><td><span class="tx-tag">${escapeHtml(data.sub)}</span></td>
      <td>${data.date}</td><td style="text-align:right"><b style="${data.income ? 'color:var(--green)' : ''}">${data.income ? '+' : ''}${money(operation.amount)}</b></td></tr>`;
  }

  async function hydrateOperations() {
    const operations = await request(`/groups/${GROUP_ID}/operations`);
    const tbody = document.getElementById('tx-table-body');
    if (tbody) tbody.innerHTML = operations.map(operationTableRow).join('');
    const list = document.getElementById('tx-list');
    if (list) list.innerHTML = operations.slice(0, 5).map(operationRow).join('');
    if (location.pathname.endsWith('finances.html')) {
      const expenses = operations.filter((item) => item.type === 'expense').reduce((sum, item) => sum + item.amount, 0);
      const incomes = operations.filter((item) => item.type === 'income').reduce((sum, item) => sum + item.amount, 0);
      const cards = document.querySelectorAll('.stats .stat-value');
      if (cards[0]) cards[0].textContent = money(expenses);
      if (cards[1]) cards[1].textContent = money(incomes);
      if (cards[2]) cards[2].textContent = money(incomes - expenses);
    }
    return operations;
  }

  async function hydrateDashboard() {
    if (!location.pathname.endsWith('/index.html') && !location.pathname.endsWith('/app/')) return;
    const dashboard = await request(`/groups/${GROUP_ID}/dashboard`);
    const cards = document.querySelectorAll('.stats .stat-value');
    if (cards[0]) cards[0].textContent = money(dashboard.summary.total_expenses);
    if (cards[1]) cards[1].textContent = money(dashboard.summary.user_expenses);
    if (cards[2]) cards[2].textContent = `+${money(dashboard.summary.owed_to_user)}`;
    if (cards[3]) cards[3].textContent = `−${money(dashboard.summary.user_owes)}`;
  }

  function balanceRows(items) {
    return items.map((item) => {
      const own = item.user_id === USER_ID;
      const label = item.balance > 0 ? `${own ? 'вам должны' : 'получит'} ${money(item.balance)}`
        : item.balance < 0 ? `${own ? 'вы должны' : 'должен'} ${money(Math.abs(item.balance))}` : 'в балансе';
      const cls = item.balance > 0 ? 'owed' : item.balance < 0 ? 'owe' : 'neutral';
      return `<div class="bal-row"><div class="bal-avatar">${own ? '🙂' : '👤'}</div>
        <div class="bal-name"><b>${escapeHtml(item.user_name)}</b><span>${own ? 'Текущий пользователь' : 'Участник группы'}</span></div>
        <div class="bal-amount ${cls}">${label}</div></div>`;
    }).join('');
  }

  async function hydrateBalances() {
    const data = await request(`/groups/${GROUP_ID}/balances`);
    const balancePanel = [...document.querySelectorAll('.panel')]
      .find((panel) => panel.querySelector('.panel-head h3')?.textContent.includes('Балансы участников'));
    if (balancePanel) {
      balancePanel.querySelectorAll('.bal-row').forEach((row) => row.remove());
      balancePanel.insertAdjacentHTML('beforeend', balanceRows(data.balances));
    }
    if (location.pathname.endsWith('balances.html')) {
      const incoming = data.recommended_transfers.filter((item) => item.to_user_id === USER_ID);
      const outgoing = data.recommended_transfers.filter((item) => item.from_user_id === USER_ID);
      const values = document.querySelectorAll('.stats .stat-value');
      const incomingTotal = incoming.reduce((sum, item) => sum + item.amount, 0);
      const outgoingTotal = outgoing.reduce((sum, item) => sum + item.amount, 0);
      if (values[0]) values[0].textContent = `+${money(incomingTotal)}`;
      if (values[1]) values[1].textContent = `−${money(outgoingTotal)}`;
      if (values[2]) values[2].textContent = `${incomingTotal - outgoingTotal >= 0 ? '+' : '−'}${money(Math.abs(incomingTotal - outgoingTotal))}`;
    }
    return data;
  }

  async function hydrateAnalytics() {
    const data = await request(`/groups/${GROUP_ID}/analytics`);
    const total = document.querySelector('.trend-total');
    if (total) total.firstChild.textContent = `${money(data.total)} `;
    const categoryPanel = [...document.querySelectorAll('.panel')]
      .find((panel) => panel.querySelector('.panel-head h3')?.textContent.includes('Расходы по категориям'));
    const legend = categoryPanel?.querySelector('.chart-wrap > div');
    if (legend) {
      legend.innerHTML = data.by_category.map((item, index) => `<div class="legend-row">
        <span class="legend-left"><span class="legend-dot" style="background:${['#4ea3e8','#3fbf8f','#f2b84b','#e05c5c','#c9cfcb'][index % 5]}"></span>${escapeHtml(item.name)}</span>
        <span class="legend-pct">${data.total ? Math.round(item.amount / data.total * 100) : 0}%</span><span class="legend-val">${money(item.amount)}</span></div>`).join('');
    }
    const userPanel = [...document.querySelectorAll('.panel')]
      .find((panel) => panel.querySelector('.panel-head h3')?.textContent.includes('Траты по участникам'));
    if (userPanel) {
      userPanel.querySelectorAll('.bal-row').forEach((row) => row.remove());
      userPanel.insertAdjacentHTML('beforeend', data.by_user.map((item) => `<div class="bal-row"><div class="bal-avatar">👤</div><div class="bal-name"><b>${escapeHtml(memberName(item.user_id))}</b></div><div class="bal-amount">${money(item.amount)}</div></div>`).join(''));
    }
  }

  async function hydrateDebts() {
    const data = await request(`/groups/${GROUP_ID}/debts`);
    const list = document.getElementById('debt-list');
    if (!list) return;
    const items = [
      ...data.calculated.map((item) => ({ debtor_id: item.from_user_id, creditor_id: item.to_user_id, amount: item.amount, description: 'Рассчитано по общим расходам' })),
      ...data.direct.filter((item) => item.status === 'active'),
    ];
    list.innerHTML = items.map((item) => {
      const incoming = item.creditor_id === USER_ID;
      const outgoing = item.debtor_id === USER_ID;
      const title = incoming ? `${memberName(item.debtor_id)} должен вам` : outgoing ? `Вы должны ${memberName(item.creditor_id)}` : `${memberName(item.debtor_id)} → ${memberName(item.creditor_id)}`;
      return `<div class="debt-card ${incoming ? 'in' : 'out'}"><div class="dir">${incoming ? '↓' : '↑'}</div>
        <div class="info"><b>${escapeHtml(title)}</b><span>${escapeHtml(item.description || 'Без комментария')}</span></div>
        <div class="amt">${incoming ? '+' : outgoing ? '−' : ''}${money(item.amount)}</div></div>`;
    }).join('') || '<p style="color:var(--text-muted)">Активных долгов нет</p>';
  }

  async function hydrateMembers() {
    if (!location.pathname.endsWith('members.html')) return;
    const grid = document.querySelector('.content .grid-2');
    if (!grid) return;
    grid.innerHTML = state.members.map((member, index) => `<div class="member-card">
      <div class="member-avatar">${member.avatar_url ? `<img src="${escapeHtml(member.avatar_url)}" alt="">` : '👤'}</div>
      <div class="member-info"><b>${escapeHtml(member.name)}</b><span>Участник группы</span></div>
      <span class="member-role ${index ? 'guest' : ''}">${index ? 'Участник' : 'Админ'}</span></div>`).join('');
    const button = document.querySelector('.page-head .primary-btn');
    button?.addEventListener('click', async () => {
      const name = prompt('Имя нового участника');
      if (!name?.trim()) return;
      try {
        await request(`/groups/${GROUP_ID}/members`, { method: 'POST', body: JSON.stringify({ name: name.trim() }) });
        notify('Участник добавлен');
        location.reload();
      } catch (error) { notify(error.message, true); }
    });
  }

  function enhanceOperationForm() {
    const form = document.getElementById('modal-form');
    const category = document.getElementById('modal-category');
    if (!form || !category) return;
    const custom = document.createElement('input');
    custom.id = 'api-custom-category'; custom.placeholder = 'Своя категория'; custom.hidden = true;
    category.parentElement.appendChild(custom);
    category.addEventListener('change', () => { custom.hidden = category.value !== '__custom'; });
    const ensureCustomCategory = () => {
      if (!category.querySelector('option[value="__custom"]')) {
        category.insertAdjacentHTML('beforeend', '<option value="__custom">Своя категория…</option>');
      }
    };
    ensureCustomCategory();
    document.querySelectorAll('[data-open-modal], .type-toggle button[data-type]').forEach((button) => {
      button.addEventListener('click', () => setTimeout(ensureCustomCategory));
    });
    const whoField = document.getElementById('modal-who')?.closest('.field');
    const split = document.createElement('div');
    split.id = 'api-split'; split.className = 'field';
    split.innerHTML = '<label>Распределение расхода</label><select id="api-split-type"><option value="equal">Поровну</option><option value="custom">По суммам</option><option value="percentage">По процентам</option></select><div id="api-participants"></div>';
    whoField?.insertAdjacentElement('afterend', split);
    renderParticipants();
    split.querySelector('select').addEventListener('change', renderParticipants);
  }

  function renderParticipants() {
    const box = document.getElementById('api-participants');
    if (!box) return;
    const type = document.getElementById('api-split-type')?.value || 'equal';
    box.innerHTML = state.members.map((member) => `<label class="api-share"><input type="checkbox" data-member="${escapeHtml(member.id)}" checked> <span>${escapeHtml(member.name)}</span>${type === 'equal' ? '' : `<input type="number" data-share="${escapeHtml(member.id)}" min="0" step="0.01" placeholder="${type === 'percentage' ? '%' : '₽'}">`}</label>`).join('');
  }

  async function submitOperation(event) {
    event.preventDefault(); event.stopImmediatePropagation();
    const amount = Number(document.getElementById('modal-amount')?.value);
    const categorySelect = document.getElementById('modal-category');
    const category = categorySelect?.value === '__custom' ? document.getElementById('api-custom-category')?.value.trim() : categorySelect?.value;
    const payer = document.getElementById('modal-who')?.value || USER_ID;
    const type = document.querySelector('#modal-overlay .type-toggle button.active')?.dataset.type || 'expense';
    const splitType = document.getElementById('api-split-type')?.value || 'equal';
    const selected = [...document.querySelectorAll('#api-participants input[type="checkbox"]:checked')].map((input) => input.dataset.member);
    const participantIds = type === 'income' ? [payer] : selected;
    const shares = type === 'expense' && splitType !== 'equal' ? participantIds.map((id) => ({ user_id: id, [splitType === 'custom' ? 'amount' : 'percentage']: Number(document.querySelector(`[data-share="${CSS.escape(id)}"]`)?.value) })) : undefined;
    const payload = {
      type, title: document.getElementById('modal-comment')?.value.trim() || category,
      amount, category: category || 'Другое', payer_id: payer, participant_ids: participantIds,
      split_type: type === 'income' ? 'equal' : splitType, shares,
      operation_date: document.getElementById('modal-date')?.value || new Date().toISOString().slice(0, 10),
      comment: document.getElementById('modal-comment')?.value.trim() || null,
    };
    try {
      await request(`/groups/${GROUP_ID}/operations`, { method: 'POST', body: JSON.stringify(payload) });
      if (typeof window.closeModal === 'function') window.closeModal();
      notify(type === 'income' ? 'Доход добавлен' : 'Расход добавлен');
      await Promise.all([hydrateOperations(), hydrateDashboard(), hydrateBalances(), hydrateAnalytics()]);
    } catch (error) { notify(error.message, true); }
  }

  async function submitDebt(event) {
    event.preventDefault(); event.stopImmediatePropagation();
    const other = document.getElementById('debt-who')?.value;
    const dir = document.querySelector('#debt-modal-overlay .type-toggle button.active')?.dataset.dir || 'in';
    const payload = {
      debtor_id: dir === 'in' ? other : USER_ID,
      creditor_id: dir === 'in' ? USER_ID : other,
      amount: Number(document.getElementById('debt-amount')?.value),
      description: document.getElementById('debt-comment')?.value.trim() || 'Прямой долг',
      due_date: document.getElementById('debt-date')?.value || null,
    };
    try {
      await request(`/groups/${GROUP_ID}/debts`, { method: 'POST', body: JSON.stringify(payload) });
      if (typeof window.closeDebtModal === 'function') window.closeDebtModal();
      notify('Долг добавлен'); await Promise.all([hydrateDebts(), hydrateBalances(), hydrateDashboard()]);
    } catch (error) { notify(error.message, true); }
  }

  function bindAiChat() {
    const panel = document.querySelector('.panel.ai-chat');
    if (!panel) return;
    const fullPageMessages = panel.firstElementChild?.querySelector('.ai-msg') ? panel.firstElementChild : null;
    let messages = fullPageMessages;
    if (!messages) {
      panel.querySelectorAll(':scope > .ai-msg').forEach((message) => message.remove());
      messages = document.createElement('div');
      messages.className = 'api-ai-messages';
      const suggestions = panel.querySelector('.ai-suggest');
      panel.insertBefore(messages, suggestions || panel.firstChild);
    }
    const input = panel?.querySelector('.ai-input input');
    const send = panel?.querySelector('.ai-input .send');
    if (!messages || !input || !send) return;
    messages.innerHTML = '<div class="ai-msg">Привет! Я финансовый помощник DeepSeek. Спросите меня о расходах, долгах или попросите добавить операцию.</div>';
    let conversationId = sessionStorage.getItem('krug_conversation_id');
    const sendMessage = async (text) => {
      if (!text.trim() || send.dataset.busy) return;
      messages.insertAdjacentHTML('beforeend', `<div class="ai-msg me">${escapeHtml(text)}</div>`);
      input.value = ''; send.dataset.busy = '1'; input.disabled = true;
      const waiting = document.createElement('div'); waiting.className = 'ai-msg'; waiting.textContent = 'Думаю…'; messages.appendChild(waiting);
      try {
        const response = await request(`/groups/${GROUP_ID}/assistant`, { method: 'POST', body: JSON.stringify({ message: text, conversation_id: conversationId }) });
        conversationId = response.conversation_id;
        sessionStorage.setItem('krug_conversation_id', conversationId);
        waiting.textContent = response.answer;
        if (response.pending_action) waiting.dataset.actionId = response.pending_action.action_id;
      } catch (error) { waiting.textContent = `Ошибка: ${error.message}`; }
      finally { delete send.dataset.busy; input.disabled = false; input.focus(); messages.scrollTop = messages.scrollHeight; }
    };
    send.addEventListener('click', () => sendMessage(input.value));
    input.addEventListener('keydown', (event) => { if (event.key === 'Enter') sendMessage(input.value); });
    panel.querySelectorAll('.ai-suggest button').forEach((button) => button.addEventListener('click', () => sendMessage(button.textContent)));
    document.querySelector('.action-btn.ai')?.addEventListener('click', () => { location.href = 'ai-assistant.html'; });
  }

  async function bindSettings() {
    if (!location.pathname.endsWith('settings.html')) return;
    const panels = document.querySelectorAll('.content .panel');
    const apartment = panels[0];
    const nameInput = apartment?.querySelector('input[type="text"]');
    const currencySelect = apartment?.querySelector('select');
    const userSettings = await request(`/users/${USER_ID}/settings`);
    if (nameInput) nameInput.value = state.group.name;
    if (currencySelect) currencySelect.value = userSettings.currency === 'USD' ? 'Доллар США ($)' : userSettings.currency === 'EUR' ? 'Евро (€)' : 'Российский рубль (₽)';
    const notifications = [...panels].find((panel) => panel.querySelector('h3')?.textContent === 'Уведомления');
    notifications?.remove();
    const profileName = document.getElementById('api-user-name');
    const profileAvatar = document.getElementById('api-avatar-url');
    const applyProfileValues = () => {
      profileName.defaultValue = profileName.value = userSettings.name || currentMember()?.name || 'Алексей';
      profileAvatar.defaultValue = profileAvatar.value = userSettings.avatar_url || '';
    };
    applyProfileValues();
    setTimeout(applyProfileValues, 100);
    const subtitle = document.querySelector('.page-head p');
    if (subtitle) subtitle.textContent = 'Название группы, профиль и валюта';
    const save = document.createElement('button'); save.className = 'primary-btn'; save.textContent = 'Сохранить настройки'; apartment?.appendChild(save);
    save.addEventListener('click', async () => {
      try {
        await Promise.all([
          request(`/groups/${GROUP_ID}/settings`, { method: 'PATCH', body: JSON.stringify({ name: nameInput.value }) }),
          request(`/users/${USER_ID}/settings`, { method: 'PATCH', body: JSON.stringify({
            name: document.getElementById('api-user-name').value,
            avatar_url: document.getElementById('api-avatar-url').value || null,
            currency: currencySelect.selectedIndex === 1 ? 'USD' : currencySelect.selectedIndex === 2 ? 'EUR' : 'RUB',
          }) }),
        ]);
        notify('Настройки сохранены');
      } catch (error) { notify(error.message, true); }
    });
  }

  function bindReceipt() {
    document.querySelector('.action-btn.receipt')?.addEventListener('click', async () => {
      const qr = prompt('Вставьте строку QR-кода чека');
      if (!qr) return;
      try {
        const draft = await request('/receipts/parse', { method: 'POST', body: JSON.stringify({ qr_data: qr }) });
        if (typeof window.openModal === 'function') window.openModal('expense');
        document.getElementById('modal-amount').value = draft.amount;
        document.getElementById('modal-comment').value = draft.merchant;
        notify('Чек распознан. Проверьте черновик.');
      } catch (error) { notify(error.message, true); }
    });
  }

  document.addEventListener('submit', (event) => {
    if (event.target.id === 'modal-form') submitOperation(event);
    if (event.target.id === 'debt-form') submitDebt(event);
  }, true);

  document.addEventListener('DOMContentLoaded', async () => {
    try {
      await loadContext();
      enhanceOperationForm();
      await Promise.all([hydrateOperations(), hydrateDashboard(), hydrateBalances(), hydrateAnalytics(), hydrateDebts()]);
      await hydrateMembers();
      await bindSettings();
      bindAiChat(); bindReceipt();
      document.querySelectorAll('.topbar-right .icon-btn').forEach((item) => item.remove());
      const profileName = document.getElementById('api-user-name');
      if (profileName && !profileName.value) profileName.value = state.members.find((member) => member.id === USER_ID)?.name || 'Алексей';
      document.body.dataset.backend = 'connected';
    } catch (error) {
      notify(`Backend недоступен: ${error.message}`, true);
    }
  });
})();
