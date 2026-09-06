/* Backend integration for the static hackathon UI. */
(() => {
  document.documentElement.classList.add('api-loading');
  const API = '/api';
  const GROUP_ID = localStorage.getItem('krug_group_id');
  const USER_ID = localStorage.getItem('krug_user_id');
  if (!GROUP_ID || !USER_ID) {
    location.replace('onboarding.html');
    return;
  }
  const state = { members: [], group: null, operations: [], analyticsMonths: 6 };
  const monthGenitive = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'];
  const monthPrepositional = ['январе', 'феврале', 'марте', 'апреле', 'мае', 'июне', 'июле', 'августе', 'сентябре', 'октябре', 'ноябре', 'декабре'];

  const escapeHtml = (value) => String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');
  const money = (value) => `${Number(value || 0).toLocaleString('ru-RU', { maximumFractionDigits: 2 })} ₽`;
  const formatDate = (value) => new Date(`${value}T00:00:00`).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
  const memberName = (id) => state.members.find((member) => member.id === id)?.name || id;
  const memberInitial = (id) => memberName(id).trim().charAt(0).toUpperCase();
  const currentMember = () => state.members.find((member) => member.id === USER_ID);
  const currentMonth = () => monthGenitive[new Date().getMonth()];
  const periodLabel = (months) => months === 12 ? 'за год' : months === 6 ? 'за 6 месяцев' : 'за 3 месяца';

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
    const avatarColors = ['#f6cf8e', '#f0b7b0', '#a9d3e5', '#cfe8d7', '#ded1ef', '#f2d5aa'];
    document.querySelectorAll('.household .avatars').forEach((avatars) => {
      avatars.innerHTML = state.members.map((member, index) => {
        const content = escapeHtml(member.name.trim().charAt(0).toUpperCase());
        return `<span title="${escapeHtml(member.name)}" style="background:${avatarColors[index % avatarColors.length]}">${content}</span>`;
      }).join('');
    });
    document.querySelectorAll('.household .info').forEach((info) => {
      const title = info.querySelector('b');
      const subtitle = info.querySelector('span');
      if (title) title.childNodes[0].textContent = `${state.group.name} `;
      if (subtitle) {
        const count = state.members.length;
        const word = count % 10 === 1 && count % 100 !== 11 ? 'участник'
          : [2, 3, 4].includes(count % 10) && ![12, 13, 14].includes(count % 100) ? 'участника' : 'участников';
        subtitle.textContent = `${count} ${word}`;
      }
    });
    document.querySelectorAll('.user-chip').forEach((chip) => {
      const avatar = chip.querySelector('.av');
      chip.childNodes.forEach((node) => {
        if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
          node.textContent = ` ${currentMember()?.name || 'Пользователь'} `;
        }
      });
      if (avatar) avatar.textContent = memberInitial(USER_ID);
      chip.querySelector('svg')?.remove();
      chip.removeAttribute('data-clickable');
      chip.classList.remove('api-user-static');
      chip.classList.add('api-user-menu-trigger');
    });
    bindGroupMembersMenu();
    bindProfileMenu();
    populateMemberSelects();
  }

  function bindProfileMenu() {
    document.querySelectorAll('.user-chip').forEach((chip) => {
      if (chip.dataset.profileBound) return;
      chip.dataset.profileBound = '1';
      const menu = document.createElement('div');
      menu.className = 'api-profile-menu';
      menu.innerHTML = `<div><span class="api-profile-avatar">${escapeHtml(memberInitial(USER_ID))}</span><span><b>${escapeHtml(currentMember()?.name || 'Пользователь')}</b><small>Участник группы</small></span></div><button type="button">Выйти из профиля</button>`;
      chip.appendChild(menu);
      chip.addEventListener('click', (event) => {
        event.stopPropagation();
        menu.classList.toggle('open');
      });
      menu.querySelector('button').addEventListener('click', (event) => {
        event.stopPropagation();
        localStorage.removeItem('krug_group_id');
        localStorage.removeItem('krug_user_id');
        sessionStorage.removeItem('krug_conversation_id');
        location.replace('onboarding.html');
      });
      document.addEventListener('click', () => menu.classList.remove('open'));
    });
  }

  function bindFinanceNavigation() {
    const sidebar = document.querySelector('.sidebar');
    const finance = sidebar?.querySelector('.nav-item[href="finances.html"]:not(.nav-sub)');
    if (!sidebar || !finance) return;
    finance.removeAttribute('data-clickable');
    finance.setAttribute('href', '#');
    finance.setAttribute('aria-expanded', 'false');
    finance.insertAdjacentHTML('beforeend', '<span class="api-finance-arrow">⌄</span>');
    const financePage = ['finances.html', 'operations.html', 'balances.html', 'analytics.html', 'debts.html'].some((page) => location.pathname.endsWith(page));
    const setOpen = (open) => {
      sidebar.classList.toggle('finance-open', open);
      finance.setAttribute('aria-expanded', String(open));
    };
    setOpen(financePage);
    finance.addEventListener('click', (event) => {
      event.preventDefault();
      setOpen(!sidebar.classList.contains('finance-open'));
    });
  }

  function updateCurrentDates() {
    const now = new Date();
    const month = currentMonth();
    const previous = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const next = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    const pageSubtitle = document.querySelector('.page-head p');
    if (pageSubtitle && location.pathname.endsWith('finances.html')) pageSubtitle.textContent = `Общий обзор бюджета группы за ${month}`;
    if (pageSubtitle && location.pathname.endsWith('operations.html')) pageSubtitle.textContent = `Все расходы и доходы группы за ${month}`;
    const dashboardSubs = document.querySelectorAll('.stats .stat-sub');
    if (location.pathname.endsWith('index.html') || location.pathname.endsWith('/app/')) {
      if (dashboardSubs[0]?.firstChild) dashboardSubs[0].firstChild.textContent = `за ${month} `;
      if (dashboardSubs[1]?.firstChild) dashboardSubs[1].firstChild.textContent = `в ${monthPrepositional[new Date().getMonth()]} `;
    }
    document.querySelectorAll('.ai-suggest button').forEach((button) => {
      if (button.textContent.includes('Проанализируй')) button.textContent = `Проанализируй наши расходы за ${month}`;
      if (button.textContent.includes('Сравни')) button.textContent = `Сравни ${month} с ${monthPrepositional[previous.getMonth()]}`;
      if (button.textContent.includes('Составь бюджет')) button.textContent = `Составь бюджет на ${monthGenitive[next.getMonth()]}`;
    });
  }

  function bindGroupMembersMenu() {
    document.querySelectorAll('.household').forEach((household) => {
      if (household.dataset.membersBound) return;
      household.dataset.membersBound = '1';
      household.removeAttribute('data-clickable');
      household.style.overflow = 'visible';
      const menu = document.createElement('div');
      menu.className = 'api-members-menu';
      menu.innerHTML = `<b>${escapeHtml(state.group.name)}</b>` + state.members.map((member) =>
        `<div><span>${escapeHtml(memberInitial(member.id))}</span>${escapeHtml(member.name)}${member.id === USER_ID ? '<small>Вы</small>' : ''}</div>`).join('');
      household.appendChild(menu);
      household.addEventListener('click', (event) => {
        event.stopPropagation();
        menu.classList.toggle('open');
      });
      document.addEventListener('click', () => menu.classList.remove('open'));
    });
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
    state.operations = operations;
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

  function bindOperationFilters() {
    if (!location.pathname.endsWith('operations.html')) return;
    const selects = document.querySelectorAll('.filters select');
    const tbody = document.getElementById('tx-table-body');
    if (selects.length < 3 || !tbody) return;
    const categories = [...new Set(state.operations.map((item) => item.category))].sort();
    const months = [...new Set(state.operations.map((item) => item.operation_date.slice(0, 7)))].sort().reverse();
    selects[0].innerHTML = '<option value="">Все категории</option>' + categories.map((item) => `<option>${escapeHtml(item)}</option>`).join('');
    selects[1].innerHTML = '<option value="">Все участники</option>' + state.members.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join('');
    selects[2].innerHTML = '<option value="">Все месяцы</option>' + months.map((item) => {
      const [year, month] = item.split('-').map(Number);
      const name = monthGenitive[month - 1];
      return `<option value="${item}">${name.charAt(0).toUpperCase()}${name.slice(1)} ${year}</option>`;
    }).join('');
    const apply = () => {
      const filtered = state.operations.filter((item) => (!selects[0].value || item.category === selects[0].value)
        && (!selects[1].value || item.payer_id === selects[1].value)
        && (!selects[2].value || item.operation_date.startsWith(selects[2].value)));
      tbody.innerHTML = filtered.map(operationTableRow).join('') || '<tr><td colspan="5">Операций не найдено</td></tr>';
    };
    selects.forEach((select) => select.addEventListener('change', apply));
  }

  async function hydrateDashboard() {
    if (!location.pathname.endsWith('/index.html') && !location.pathname.endsWith('/app/')) return;
    const dashboard = await request(`/groups/${GROUP_ID}/dashboard`);
    const cards = document.querySelectorAll('.stats .stat-value');
    if (cards[0]) cards[0].textContent = money(dashboard.summary.total_expenses);
    if (cards[1]) cards[1].textContent = money(dashboard.summary.user_expenses);
    if (cards[2]) cards[2].textContent = `+${money(dashboard.summary.owed_to_user)}`;
    if (cards[3]) cards[3].textContent = `−${money(dashboard.summary.user_owes)}`;
    const subs = document.querySelectorAll('.stats .stat-sub');
    if (subs[2]) subs[2].firstChild.textContent = `${dashboard.summary.owed_to_user > 0 ? 'есть долги' : 'нет долгов'} `;
    if (subs[3]) subs[3].firstChild.textContent = `${dashboard.summary.user_owes > 0 ? 'есть долги' : 'нет долгов'} `;
  }

  function balanceRows(items) {
    return items.map((item) => {
      const own = item.user_id === USER_ID;
      const label = item.balance > 0 ? `${own ? 'вам должны' : 'получит'} ${money(item.balance)}`
        : item.balance < 0 ? `${own ? 'вы должны' : 'должен'} ${money(Math.abs(item.balance))}` : 'в балансе';
      const cls = item.balance > 0 ? 'owed' : item.balance < 0 ? 'owe' : 'neutral';
      return `<div class="bal-row"><div class="bal-avatar">${escapeHtml(memberInitial(item.user_id))}</div>
        <div class="bal-name"><b>${escapeHtml(item.user_name)}</b><span>${own ? 'Текущий пользователь' : 'Участник группы'}</span></div>
        <div class="bal-amount ${cls}">${label}</div></div>`;
    }).join('');
  }

  async function hydrateBalances() {
    const [data, operations] = await Promise.all([
      request(`/groups/${GROUP_ID}/balances`),
      request(`/groups/${GROUP_ID}/operations`),
    ]);
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
      const groupIncome = operations.filter((item) => item.type === 'income').reduce((sum, item) => sum + item.amount, 0);
      const groupExpenses = operations.filter((item) => item.type === 'expense').reduce((sum, item) => sum + item.amount, 0);
      const groupTotal = groupIncome - groupExpenses;
      if (values[0]) values[0].textContent = `+${money(incomingTotal)}`;
      if (values[1]) values[1].textContent = `−${money(outgoingTotal)}`;
      if (values[2]) values[2].textContent = `${groupTotal >= 0 ? '+' : '−'}${money(Math.abs(groupTotal))}`;
      const subtitles = document.querySelectorAll('.stats .stat-sub');
      if (subtitles[0]) subtitles[0].textContent = incoming.length ? `${incoming.length} ${incoming.length === 1 ? 'человек' : 'человека'}` : 'нет долгов';
      if (subtitles[1]) subtitles[1].textContent = outgoing.length ? `${outgoing.length} ${outgoing.length === 1 ? 'человек' : 'человека'}` : 'нет долгов';
      const pagePanel = [...document.querySelectorAll('.content .panel')]
        .find((panel) => panel.querySelector('.panel-head h3')?.textContent.includes('Балансы участников'));
      let transfersPanel = document.getElementById('api-transfers');
      if (!transfersPanel) {
        transfersPanel = document.createElement('div');
        transfersPanel.id = 'api-transfers'; transfersPanel.className = 'panel';
        pagePanel?.insertAdjacentElement('afterend', transfersPanel);
      }
      transfersPanel.innerHTML = '<div class="panel-head"><h3>Рекомендованные переводы</h3></div>'
        + (data.recommended_transfers.map((item) => `<div class="bal-row"><div class="bal-avatar">↗</div>
          <div class="bal-name"><b>${escapeHtml(item.from_user_name)} → ${escapeHtml(item.to_user_name)}</b><span>Для сведения общего баланса</span></div>
          <div class="bal-amount">${money(item.amount)}</div>${item.from_user_id === USER_ID ? `<button class="primary-btn api-pay" data-to="${escapeHtml(item.to_user_id)}" data-amount="${item.amount}">Отметить перевод</button>` : ''}</div>`).join('') || '<p>Все расчёты закрыты</p>');
      transfersPanel.querySelectorAll('.api-pay').forEach((button) => button.addEventListener('click', async () => {
        try {
          await request(`/groups/${GROUP_ID}/payments`, { method: 'POST', body: JSON.stringify({ from_user_id: USER_ID, to_user_id: button.dataset.to, amount: Number(button.dataset.amount), comment: 'Отмечено во frontend' }) });
          notify('Перевод учтён'); await Promise.all([hydrateBalances(), hydrateDashboard(), hydrateDebts()]);
        } catch (error) { notify(error.message, true); }
      }));
    }
    return data;
  }

  function analyticsMonthKeys(count) {
    const now = new Date();
    return Array.from({ length: count }, (_, index) => {
      const date = new Date(now.getFullYear(), now.getMonth() - count + index + 1, 1);
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    });
  }

  function bindAnalyticsPeriods() {
    const selects = [...document.querySelectorAll('select')].filter((select) =>
      [...select.options].some((option) => option.textContent.includes('6 месяцев')));
    selects.forEach((select) => {
      select.innerHTML = '<option value="3">За 3 месяца</option><option value="6">За 6 месяцев</option><option value="12">За год</option>';
      select.value = String(state.analyticsMonths);
      select.addEventListener('change', async () => {
        state.analyticsMonths = Number(select.value);
        selects.forEach((item) => { item.value = select.value; });
        try { await hydrateAnalytics(); } catch (error) { notify(error.message, true); }
      });
    });
  }

  async function hydrateAnalytics() {
    const data = await request(`/groups/${GROUP_ID}/analytics?months=${state.analyticsMonths}`);
    const chartColors = ['#4ea3e8', '#3fbf8f', '#f2b84b', '#e05c5c', '#9a5fd1', '#67b86f'];
    const total = document.querySelector('.trend-total');
    if (total) {
      total.firstChild.textContent = `${money(data.total)} `;
      const label = total.querySelector('span');
      if (label) label.textContent = periodLabel(state.analyticsMonths);
    }
    const categoryPanel = [...document.querySelectorAll('.panel')]
      .find((panel) => panel.querySelector('.panel-head h3')?.textContent.includes('Расходы по категориям'));
    const legend = categoryPanel?.querySelector('.chart-wrap > div');
    const categoryChart = categoryPanel?.querySelector('.chart-wrap svg');
    if (categoryChart) {
      if (!data.total) {
        categoryChart.style.transform = '';
        categoryChart.innerHTML = '<circle cx="21" cy="21" r="15.9" fill="transparent" stroke="#dfe4e1" stroke-width="6"/>';
      } else {
        let offset = 0;
        categoryChart.innerHTML = data.by_category.map((item, index) => {
          const percent = item.amount / data.total * 100;
          const circle = `<circle cx="21" cy="21" r="15.9" fill="transparent" stroke="${chartColors[index % chartColors.length]}" stroke-width="6" pathLength="100" stroke-dasharray="${percent} ${100 - percent}" stroke-dashoffset="-${offset}"/>`;
          offset += percent;
          return circle;
        }).join('');
        categoryChart.style.transform = 'rotate(-90deg)';
      }
    }
    if (legend) {
      legend.innerHTML = data.by_category.map((item, index) => `<div class="legend-row">
        <span class="legend-left"><span class="legend-dot" style="background:${chartColors[index % chartColors.length]}"></span>${escapeHtml(item.name)}</span>
        <span class="legend-pct">${Math.round(item.amount / data.total * 100)}%</span><span class="legend-val">${money(item.amount)}</span></div>`).join('')
        || '<div class="api-empty-chart">Категории появятся после первого расхода</div>';
    }
    const trendPanel = [...document.querySelectorAll('.panel')]
      .find((panel) => panel.querySelector('.panel-head h3')?.textContent.includes('Динамика расходов'));
    const trendChart = trendPanel?.querySelector('svg');
    if (trendChart) {
      const keys = analyticsMonthKeys(state.analyticsMonths);
      const amounts = new Map(data.by_month.map((item) => [item.month, item.amount]));
      const values = keys.map((key) => ({ key, amount: amounts.get(key) || 0 }));
      const max = Math.max(...values.map((item) => item.amount), 0);
      const labels = trendChart.nextElementSibling;
      if (labels) {
        labels.classList.add('api-month-labels');
        labels.innerHTML = values.map((item) => {
          const month = Number(item.key.slice(5));
          return `<span>${escapeHtml(monthGenitive[month - 1].slice(0, 3))}</span>`;
        }).join('');
      }
      if (!max) {
        trendChart.style.display = 'none';
        if (!trendPanel.querySelector('.api-trend-empty')) {
          trendChart.insertAdjacentHTML('beforebegin', '<div class="api-trend-empty">Пока нет расходов за выбранный период</div>');
        }
      } else {
        trendPanel.querySelector('.api-trend-empty')?.remove();
        trendChart.style.display = '';
        const viewBox = (trendChart.getAttribute('viewBox') || '0 0 260 110').split(/\s+/).map(Number);
        const width = viewBox[2];
        const height = viewBox[3];
        const slot = (width - 20) / values.length;
        const barWidth = Math.max(5, slot * 0.58);
        trendChart.innerHTML = values.map((item, index) => {
          const barHeight = item.amount ? Math.max(3, item.amount / max * (height - 30)) : 0;
          const x = 10 + index * slot + (slot - barWidth) / 2;
          const y = height - 15 - barHeight;
          return `<rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="${Math.min(4, barWidth / 4)}" fill="#1a7a4c"><title>${escapeHtml(monthGenitive[Number(item.key.slice(5)) - 1])}: ${money(item.amount)}</title></rect>`;
        }).join('');
      }
    }
    const userPanel = [...document.querySelectorAll('.panel')]
      .find((panel) => panel.querySelector('.panel-head h3')?.textContent.includes('Траты по участникам'));
    if (userPanel) {
      userPanel.querySelectorAll('.bal-row, .api-empty-chart').forEach((row) => row.remove());
      userPanel.insertAdjacentHTML('beforeend', data.by_user.map((item) => `<div class="bal-row"><div class="bal-avatar">${escapeHtml(memberInitial(item.user_id))}</div><div class="bal-name"><b>${escapeHtml(memberName(item.user_id))}</b></div><div class="bal-amount">${money(item.amount)}</div></div>`).join('') || '<div class="api-empty-chart">Нет расходов участников за выбранный период</div>');
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
      <div class="member-avatar">${escapeHtml(memberInitial(member.id))}</div>
      <div class="member-info"><b>${escapeHtml(member.name)}</b><span>Участник группы</span></div>
      <span class="member-role ${index ? 'guest' : ''}">${index ? 'Участник' : 'Админ'}</span></div>`).join('');
    document.getElementById('invite-member-btn')?.addEventListener('click', openInviteDialog);
  }

  function openInviteDialog() {
    document.getElementById('api-invite-modal')?.remove();
    const inviteUrl = `${location.origin}/app/onboarding.html?invite=${encodeURIComponent(GROUP_ID)}`;
    const overlay = document.createElement('div');
    overlay.id = 'api-invite-modal';
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `<div class="modal">
      <div class="modal-head"><h3>Пригласить участника</h3><button type="button" class="modal-close" aria-label="Закрыть">×</button></div>
      <p class="api-invite-note">Отправьте эту ссылку человеку. По ней он сможет ввести своё имя и присоединиться к группе «${escapeHtml(state.group.name)}».</p>
      <div class="api-invite-link"><input type="text" value="${escapeHtml(inviteUrl)}" readonly><button type="button" class="primary-btn compact-action">Копировать</button></div>
    </div>`;
    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('open'));
    const close = () => { overlay.classList.remove('open'); setTimeout(() => overlay.remove(), 250); };
    overlay.querySelector('.modal-close').addEventListener('click', close);
    overlay.addEventListener('click', (event) => { if (event.target === overlay) close(); });
    overlay.querySelector('.api-invite-link button').addEventListener('click', async () => {
      const input = overlay.querySelector('.api-invite-link input');
      try {
        await navigator.clipboard.writeText(inviteUrl);
      } catch (_) {
        input.select(); document.execCommand('copy');
      }
      notify('Ссылка приглашения скопирована');
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
    messages.innerHTML = '<div class="ai-msg">Привет! Я финансовый помощник. Спросите меня о расходах, долгах или попросите добавить операцию.</div>';
    let conversationId = sessionStorage.getItem('krug_conversation_id');
    const draftCard = (action) => {
      const typeNames = { expense: 'Расход', income: 'Доход', debt: 'Долг' };
      const rows = action.type === 'debt'
        ? [
          ['Сумма', money(action.amount)],
          ['Кто должен', memberName(action.debtor_id)],
          ['Кому должен', memberName(action.creditor_id)],
          ['Комментарий', action.description || 'Без комментария'],
          ['Срок', action.due_date ? formatDate(action.due_date) : 'Не указан'],
        ]
        : [
          ['Название', action.title || 'Без названия'],
          ['Сумма', money(action.amount)],
          ['Категория', action.category || 'Другое'],
          [action.type === 'income' ? 'Получатель' : 'Кто оплатил', memberName(action.payer_id)],
          ['Дата', action.operation_date ? formatDate(action.operation_date) : 'Сегодня'],
        ];
      const shares = action.shares?.length
        ? action.shares.map((share) =>
          `<li><span>${escapeHtml(memberName(share.user_id))}</span><b>${share.amount != null ? money(share.amount) : `${Number(share.percentage || 0).toLocaleString('ru-RU')}%`}</b></li>`).join('')
        : action.type === 'expense' && action.participant_ids?.length
          ? action.participant_ids.map((id) => `<li><span>${escapeHtml(memberName(id))}</span><b>${money(action.amount / action.participant_ids.length)}</b></li>`).join('')
          : '';
      return `<section class="api-ai-draft" data-action-id="${escapeHtml(action.action_id)}">
        <div class="api-ai-draft-head"><span>Черновик</span><b>${typeNames[action.type] || 'Операция'}</b></div>
        <div class="api-ai-draft-rows">${rows.map(([label, value]) => `<div><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b></div>`).join('')}</div>
        ${shares ? `<div class="api-ai-draft-split"><span>Распределение</span><ul>${shares}</ul></div>` : ''}
        <p>Проверьте данные. Они сохранятся только после подтверждения.</p>
        <div class="api-ai-draft-actions"><button type="button" class="ghost-btn api-ai-cancel">Отменить</button><button type="button" class="primary-btn api-ai-confirm">Подтвердить и сохранить</button></div>
      </section>`;
    };
    const bindDraftActions = (card) => {
      const actionId = card.dataset.actionId;
      card.querySelector('.api-ai-confirm')?.addEventListener('click', async () => {
        try {
          await request(`/groups/${GROUP_ID}/assistant/actions/${actionId}/confirm`, { method: 'POST' });
          card.innerHTML = '<div class="api-ai-draft-result success">✓ Операция сохранена</div>';
          await Promise.all([hydrateOperations(), hydrateDashboard(), hydrateBalances(), hydrateAnalytics(), hydrateDebts()]);
        } catch (error) { notify(error.message, true); }
      });
      card.querySelector('.api-ai-cancel')?.addEventListener('click', async () => {
        try {
          await request(`/groups/${GROUP_ID}/assistant/actions/${actionId}/cancel`, { method: 'POST' });
          card.innerHTML = '<div class="api-ai-draft-result">Черновик отменён</div>';
        } catch (error) { notify(error.message, true); }
      });
    };
    const sendMessage = async (text) => {
      if (!text.trim() || send.dataset.busy) return;
      messages.insertAdjacentHTML('beforeend', `<div class="ai-msg me">${escapeHtml(text)}</div>`);
      input.value = ''; send.dataset.busy = '1'; input.disabled = true;
      const waiting = document.createElement('div'); waiting.className = 'ai-msg'; waiting.textContent = 'Думаю…'; messages.appendChild(waiting);
      try {
        const response = await request(`/groups/${GROUP_ID}/assistant`, { method: 'POST', body: JSON.stringify({ message: text, conversation_id: conversationId }) });
        conversationId = response.conversation_id;
        sessionStorage.setItem('krug_conversation_id', conversationId);
        waiting.textContent = response.pending_action ? 'Проверьте подготовленный черновик:' : response.answer;
        if (response.pending_action) {
          waiting.insertAdjacentHTML('afterend', draftCard(response.pending_action));
          bindDraftActions(waiting.nextElementSibling);
        }
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
    const userSettings = await request(`/users/${USER_ID}/settings`);
    if (nameInput) nameInput.value = state.group.name;
    const notifications = [...panels].find((panel) => panel.querySelector('h3')?.textContent === 'Уведомления');
    notifications?.remove();
    [...apartment.querySelectorAll('.field')].find((field) => field.querySelector('label')?.textContent.includes('Дата закрытия'))?.remove();
    [...panels].find((panel) => panel.querySelector('h3')?.textContent === 'Участники и доступ')?.remove();
    const profileName = document.getElementById('api-user-name');
    const applyProfileValues = () => {
      profileName.defaultValue = profileName.value = userSettings.name || currentMember()?.name || 'Алексей';
    };
    applyProfileValues();
    setTimeout(applyProfileValues, 100);
    const subtitle = document.querySelector('.page-head p');
    if (subtitle) subtitle.textContent = 'Название группы и профиль';
    const save = document.createElement('button'); save.className = 'primary-btn'; save.textContent = 'Сохранить настройки'; apartment?.appendChild(save);
    save.addEventListener('click', async () => {
      try {
        await Promise.all([
          request(`/groups/${GROUP_ID}/settings`, { method: 'PATCH', body: JSON.stringify({ name: nameInput.value }) }),
          request(`/users/${USER_ID}/settings`, { method: 'PATCH', body: JSON.stringify({
            name: document.getElementById('api-user-name').value,
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
      bindFinanceNavigation();
      updateCurrentDates();
      await loadContext();
      enhanceOperationForm();
      bindAnalyticsPeriods();
      await Promise.all([hydrateOperations(), hydrateDashboard(), hydrateBalances(), hydrateAnalytics(), hydrateDebts()]);
      bindOperationFilters();
      await hydrateMembers();
      await bindSettings();
      bindAiChat(); bindReceipt();
      document.querySelectorAll('.topbar-right .icon-btn').forEach((item) => item.remove());
      const profileName = document.getElementById('api-user-name');
      if (profileName && !profileName.value) profileName.value = state.members.find((member) => member.id === USER_ID)?.name || 'Алексей';
      document.body.dataset.backend = 'connected';
      document.documentElement.classList.remove('api-loading');
    } catch (error) {
      if (String(error.message).includes('Group not found') || String(error.message).includes('not group members')) {
        localStorage.removeItem('krug_group_id');
        localStorage.removeItem('krug_user_id');
        location.replace('onboarding.html');
      } else {
        document.documentElement.classList.remove('api-loading');
        notify(`Backend недоступен: ${error.message}`, true);
      }
    }
  });
})();
