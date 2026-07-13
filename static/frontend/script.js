const API_URL = '/api/v1';
let allCompanies = [];
let currentSort = { column: 'ticker', direction: 'asc' };

// ─── Загрузка курсов валют ───
async function loadCurrencyRates() {
    const usdEl = document.getElementById('usd-rate');
    const cnyEl = document.getElementById('cny-rate');

    try {
        const response = await fetch(`${API_URL}/currency/rates`);
        if (!response.ok) throw new Error('Ошибка загрузки курсов');
        const data = await response.json();

        if (data.usd) usdEl.textContent = `💵 USD: ${data.usd.toFixed(2)} ₽`;
        else usdEl.textContent = '💵 USD: нет данных';

        if (data.cny) cnyEl.textContent = `💴 CNY: ${data.cny.toFixed(2)} ₽`;
        else cnyEl.textContent = '💴 CNY: нет данных';

        if (data.updated_at) {
            const date = new Date(data.updated_at);
            document.getElementById('currency-container').title = `Обновлено: ${date.toLocaleString('ru-RU')}`;
        }

    } catch (error) {
        usdEl.textContent = '💵 USD: ошибка';
        cnyEl.textContent = '💴 CNY: ошибка';
        console.error('Ошибка загрузки курсов:', error);
    }
}

// ─── Загрузка компаний ───
async function loadCompanies() {
    const container = document.getElementById('companies-container');
    const tableBody = document.getElementById('metrics-table-body');
    if (!tableBody) {
        console.error('❌ Элемент metrics-table-body не найден!');
        return;
    }

    container.innerHTML = '<div class="loading">⏳ Загрузка компаний...</div>';
    tableBody.innerHTML = '<tr><td colspan="6" class="loading">⏳ Загрузка данных...</td></tr>';

    try {
        const companiesRes = await fetch(`${API_URL}/companies`);
        if (!companiesRes.ok) throw new Error('Ошибка загрузки компаний');
        const companies = await companiesRes.json();

        if (companies.length === 0) {
            container.innerHTML = '<div class="loading">📭 Компании не найдены</div>';
            tableBody.innerHTML = '<tr><td colspan="6" class="loading">📭 Нет данных</td></tr>';
            return;
        }

        // Загружаем метрики для всех компаний
        allCompanies = [];
        for (const company of companies) {
            let metrics = {};
            try {
                const metricsRes = await fetch(`${API_URL}/metrics/${company.ticker}`);
                if (metricsRes.ok) {
                    metrics = await metricsRes.json();
                }
            } catch (e) {
                console.warn(`Не удалось загрузить метрики для ${company.ticker}`);
            }
            allCompanies.push({ ...company, metrics });
        }

        // Рендерим левую панель
        renderCompaniesList(allCompanies);

        // Рендерим таблицу с сортировкой
        renderTable(allCompanies);

        // Навешиваем обработчики для сортировки
        setupSorting();

    } catch (error) {
        container.innerHTML = `<div class="loading">❌ Ошибка: ${error.message}</div>`;
        tableBody.innerHTML = `<tr><td colspan="6" class="loading">❌ Ошибка: ${error.message}</td></tr>`;
        console.error('Ошибка загрузки компаний:', error);
    }
}

// ─── Рендеринг списка компаний ───
function renderCompaniesList(companies) {
    const container = document.getElementById('companies-container');
    container.innerHTML = '';

    for (const company of companies) {
        const card = document.createElement('div');
        card.className = 'company-card';
        const metrics = company.metrics || {};
        const badgeText = metrics.pe_ratio ? `P/E ${metrics.pe_ratio.toFixed(2)}` : '📊 Нет данных';
        card.innerHTML = `
            <div>
                <span class="ticker">${company.ticker}</span>
                <span class="name">${company.name}</span>
            </div>
            <span class="badge">${badgeText}</span>
        `;
        card.addEventListener('click', () => loadChartAndMetrics(company.ticker));
        container.appendChild(card);
    }
}

// ─── Рендеринг таблицы ───
function renderTable(companies) {
    const tableBody = document.getElementById('metrics-table-body');
    if (!tableBody) return;

    if (!companies || companies.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" class="loading">📭 Нет данных</td></tr>';
        return;
    }

    // Сортируем
    const sorted = sortCompanies(companies, currentSort.column, currentSort.direction);

    let html = '';
    for (const company of sorted) {
        const m = company.metrics || {};
        const pe = m.pe_ratio !== undefined && m.pe_ratio !== null ? m.pe_ratio.toFixed(2) : '—';
        const pb = m.pb_ratio !== undefined && m.pb_ratio !== null ? m.pb_ratio.toFixed(2) : '—';
        const roe = m.roe !== undefined && m.roe !== null ? m.roe.toFixed(2) + '%' : '—';
        const eps = m.eps !== undefined && m.eps !== null ? m.eps.toFixed(2) + ' ₽' : '—';
        const divYield = m.dividend_yield !== undefined && m.dividend_yield !== null ? m.dividend_yield.toFixed(2) + '%' : '—';

        html += `
            <tr>
                <td><strong>${company.ticker}</strong></td>
                <td>${pe}</td>
                <td>${pb}</td>
                <td>${roe}</td>
                <td>${eps}</td>
                <td>${divYield}</td>
            </tr>
        `;
    }

    tableBody.innerHTML = html;
}

// ─── Сортировка ───
function sortCompanies(companies, column, direction) {
    return [...companies].sort((a, b) => {
        let valA, valB;

        if (column === 'ticker') {
            valA = a.ticker;
            valB = b.ticker;
            return direction === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }

        valA = a.metrics && a.metrics[column] !== undefined ? a.metrics[column] : null;
        valB = b.metrics && b.metrics[column] !== undefined ? b.metrics[column] : null;

        if (valA === null && valB === null) return 0;
        if (valA === null) return 1;
        if (valB === null) return -1;

        return direction === 'asc' ? valA - valB : valB - valA;
    });
}

// ─── Настройка сортировки ───
function setupSorting() {
    const headers = document.querySelectorAll('#metrics-table thead th');

    // Маппинг заголовков на ключи в данных
    const columnMap = {
        'Тикер': 'ticker',
        'P/E': 'pe_ratio',
        'P/B': 'pb_ratio',
        'ROE, %': 'roe',
        'EPS, ₽': 'eps',
        'Див. доходность, %': 'dividend_yield'
    };

    headers.forEach((header) => {
        header.addEventListener('click', () => {
            const headerText = header.textContent.trim().replace('⇅', '').trim();
            const sortKey = columnMap[headerText] || 'ticker';

            if (currentSort.column === sortKey) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.column = sortKey;
                currentSort.direction = 'asc';
            }

            // Обновляем стрелки
            headers.forEach(th => {
                th.classList.remove('asc', 'desc');
                const arrow = th.querySelector('.sort-arrow');
                if (arrow) arrow.textContent = '⇅';
            });

            const arrow = header.querySelector('.sort-arrow');
            if (arrow) {
                header.classList.add(currentSort.direction);
                arrow.textContent = currentSort.direction === 'asc' ? '↑' : '↓';
            }

            renderTable(allCompanies);
        });
    });
}

// ─── Загрузка графика и метрик ───
async function loadChartAndMetrics(ticker) {
    const wrapper = document.getElementById('chart-wrapper');
    const img = document.getElementById('chart-image');
    const info = document.getElementById('chart-info');
    const hint = document.querySelector('.hint');
    const container = document.getElementById('metrics-container');

    hint.style.display = 'none';
    wrapper.style.display = 'flex';
    info.textContent = `⏳ Обновление данных для ${ticker}...`;
    img.style.display = 'none';
    container.style.display = 'none';

    try {
        const response = await fetch(`${API_URL}/update-and-calculate/${ticker}`, {
            method: 'POST'
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка обновления данных');
        }

        const data = await response.json();

        await loadChart(ticker);
        displayMetrics(data.metrics);

        const priceDate = data.price ? data.price.date : '';
        info.textContent = `✅ Данные для ${ticker} обновлены${priceDate ? ` (${priceDate})` : ''}`;

    } catch (error) {
        info.textContent = `❌ Ошибка: ${error.message}`;
        console.error('Ошибка:', error);
    }
}

// ─── Загрузка графика ───
async function loadChart(ticker) {
    const img = document.getElementById('chart-image');
    const info = document.getElementById('chart-info');

    info.textContent = '⏳ Загрузка графика...';
    img.style.display = 'none';

    try {
        const chartUrl = `${API_URL}/chart-image/${ticker}`;
        img.src = chartUrl;

        await new Promise((resolve, reject) => {
            img.onload = resolve;
            img.onerror = reject;
            setTimeout(reject, 10000);
        });

        img.style.display = 'block';
        info.textContent = `📈 ${ticker} — свечной график с MA50`;

    } catch (error) {
        img.style.display = 'none';
        info.textContent = `❌ Не удалось загрузить график для ${ticker}`;
        console.error('Ошибка загрузки графика:', error);
    }
}

// ─── Отображение детальных метрик ───
function displayMetrics(metrics) {
    const container = document.getElementById('metrics-container');
    const tbody = document.getElementById('metrics-body');

    container.style.display = 'block';

    const metricNames = {
        'pe_ratio': 'P/E (Цена / Прибыль)',
        'pb_ratio': 'P/B (Цена / Баланс)',
        'roe': 'ROE (Рентабельность капитала)',
        'eps': 'EPS (Прибыль на акцию)',
        'book_value_per_share': 'Балансовая стоимость акции',
        'dividend_yield': 'Дивидендная доходность',
        'dividend_per_share': 'Дивиденд на акцию'
    };

    tbody.innerHTML = '';
    let hasData = false;

    for (const [key, label] of Object.entries(metricNames)) {
        const value = metrics[key];
        if (value !== null && value !== undefined && value !== '') {
            hasData = true;
            const row = document.createElement('tr');
            const nameCell = document.createElement('td');
            nameCell.className = 'metric-name';
            nameCell.textContent = label;

            const valueCell = document.createElement('td');
            valueCell.className = 'metric-value';
            valueCell.textContent = formatValue(key, value);

            if (key === 'roe' && value > 15) valueCell.classList.add('good');
            if (key === 'roe' && value < 5) valueCell.classList.add('bad');
            if (key === 'dividend_yield' && value > 5) valueCell.classList.add('good');

            row.appendChild(nameCell);
            row.appendChild(valueCell);
            tbody.appendChild(row);
        }
    }

    if (!hasData) {
        tbody.innerHTML = '<tr><td colspan="2" class="loading">📭 Нет данных по метрикам</td></tr>';
    }
}

function formatValue(key, value) {
    if (value === null || value === undefined) return 'Нет данных';
    if (key === 'roe' || key === 'dividend_yield') return `${value.toFixed(2)}%`;
    if (key === 'eps' || key === 'book_value_per_share' || key === 'dividend_per_share') return `${value.toFixed(2)} ₽`;
    if (key === 'pe_ratio' || key === 'pb_ratio') return value.toFixed(2);
    return value;
}

// ─── Запускаем при загрузке страницы ───
document.addEventListener('DOMContentLoaded', () => {
    loadCurrencyRates();
    loadCompanies();
});