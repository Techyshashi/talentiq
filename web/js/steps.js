import {request, download} from './api.js';
import {createAILoader, nimoMessage} from './nimo.js';

const labels = ['Welcome', 'Job description', 'CVs', 'Stack ranking', 'Questions', 'Market', 'Search', 'Finish'];
const state = {step: 0, jd: null, cvs: [], job: null, generated: {}};
const el = (tag, text, cls) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = String(text);
  if (cls) node.className = cls;
  return node;
};
const button = (text, cls = 'primary') => {
  const node = el('button', text, cls);
  node.type = 'button';
  return node;
};
const list = (items) => {
  const node = el('ul', undefined, 'tag-list');
  (Array.isArray(items) ? items : []).forEach(item => node.append(el('li', item)));
  return node;
};
function renderNav() {
  const nav = el('div', undefined, 'steps');
  labels.forEach((name, i) => nav.append(el('span', `${i + 1}. ${name}`, `step${i === state.step ? ' active' : ''}`)));
  document.querySelector('#progress').replaceChildren(nav);
}
function actions(root, next = true) {
  const row = el('div', undefined, 'actions');
  if (state.step > 0) {
    const back = button('Back', 'ghost');
    back.onclick = () => { state.step -= 1; render(root); };
    row.append(back);
  }
  if (next) {
    const forward = button(state.step === 7 ? 'Start over' : 'Continue');
    forward.onclick = () => { state.step = state.step === 7 ? 0 : Math.min(7, state.step + 1); render(root); };
    row.append(forward);
  }
  root.append(row);
}
function fieldCard(title, value) {
  const card = el('div', undefined, 'stat');
  card.append(el('h3', title), el('p', value || 'Not stated'));
  return card;
}
function renderJD(root) {
  root.append(el('p', 'Paste a role brief or upload it. TalentIQ will turn it into a readable summary.'));
  const form = el('form'), area = el('textarea'), file = el('input'), output = el('div');
  area.placeholder = 'Paste a job description...';
  file.type = 'file';
  file.accept = '.pdf,.docx,.txt';
  const analyse = button('Analyse job description');
  const run = async () => {
    output.replaceChildren();
    const loader = createAILoader('Analyzing job description...');
    output.append(loader.element);
    analyse.disabled = true;
    try {
      const data = new FormData();
      data.append('text', area.value);
      if (file.files[0]) data.append('file', file.files[0]);
      const result = await request('/jd/analyse', {method: 'POST', body: data});
      state.jd = result.jd;
      loader.complete('Role brief understood');
      renderJDOutput(output, state.jd);
    } catch (error) {
      loader.fail(error.message, run);
    } finally {
      analyse.disabled = false;
    }
  };
  analyse.onclick = run;
  form.append(el('label', 'Job description'), area, el('label', 'Or upload a file'), file, analyse, output);
  root.append(form);
  if (state.jd) renderJDOutput(root, state.jd);
  actions(root);
}
function renderJDOutput(root, jd) {
  const section = el('section', undefined, 'structured');
  section.append(el('h3', 'What TalentIQ understood'));
  const grid = el('div', undefined, 'grid');
  [['Role', jd.role], ['Experience', jd.experience], ['Location', jd.location], ['Domain', jd.domain], ['Education', jd.education]]
    .forEach(([name, value]) => grid.append(fieldCard(name, value)));
  section.append(grid);
  const skills = el('div', undefined, 'grid');
  const must = fieldCard('Must-have skills', '');
  must.append(list(jd.must_have_skills));
  const nice = fieldCard('Nice-to-have skills', '');
  nice.append(list(jd.nice_to_have_skills));
  skills.append(must, nice);
  section.append(skills);
  root.append(section);
}
function renderCVs(root) {
  const file = el('input'), output = el('div');
  file.type = 'file';
  file.multiple = true;
  file.accept = '.pdf,.docx';
  const read = button('Read CVs');
  read.onclick = async () => {
    output.replaceChildren();
    const loader = createAILoader('Processing CVs...');
    output.append(loader.element);
    read.disabled = true;
    try {
      const form = new FormData();
      [...file.files].forEach(item => form.append('files', item));
      const result = await request('/cvs/upload', {method: 'POST', body: form});
      state.cvs = result.cvs;
      loader.complete(`${result.cvs.length} CVs ready`);
      const grid = el('div', undefined, 'grid');
      result.cvs.forEach(cv => grid.append(fieldCard(cv.filename, `${cv.characters.toLocaleString()} characters`)));
      output.append(grid);
      if (result.failed.length) output.append(el('p', `${result.failed.length} file(s) could not be read.`, 'notice'));
    } catch (error) {
      loader.fail(error.message, read);
    } finally {
      read.disabled = false;
    }
  };
  root.append(el('p', 'Upload PDF or Word CVs. Scanned or empty documents are flagged.'), file, read, output);
  actions(root);
}
function renderRanking(root) {
  const output = el('div'), start = button('Start ranking');
  const run = async () => {
    if (!state.jd || !state.cvs.length) {
      output.replaceChildren(el('p', 'Analyse a JD and upload at least one CV first.', 'error'));
      return;
    }
    output.replaceChildren();
    const loader = createAILoader('Ranking candidates...');
    output.append(loader.element);
    start.disabled = true;
    try {
      state.job = (await request('/ranking/start', {method: 'POST', body: JSON.stringify({jd: state.jd, cvs: state.cvs})})).job_id;
      const poll = async () => {
        try {
          const result = await request(`/ranking/${state.job}`);
          loader.update(`Evaluated ${result.completed} of ${result.total} CVs...`, result.total ? result.completed / result.total * 100 : 0);
          if (result.status === 'completed') {
            loader.complete('Ranking complete');
            renderCandidates(output, result.results);
            start.disabled = false;
          } else if (result.status === 'failed') {
            loader.fail(result.error || 'Ranking failed.', run);
            start.disabled = false;
          } else {
            setTimeout(poll, 800);
          }
        } catch (error) {
          loader.fail(error.message, run);
          start.disabled = false;
        }
      };
      await poll();
    } catch (error) {
      loader.fail(error.message, run);
      start.disabled = false;
    }
  };
  start.onclick = run;
  root.append(el('p', 'Compare candidates using only evidence found in each CV.'), start, output);
  actions(root);
}
function renderCandidates(root, rows) {
  root.append(el('h3', 'Recommended order'), el('p', `${rows.length} candidates evaluated`));
  const cards = el('div', undefined, 'candidate-list');
  rows.forEach(row => {
    const card = el('article', undefined, 'candidate-card');
    const top = el('div', undefined, 'candidate-top');
    top.append(el('h3', row.filename), el('strong', `${row.score}/100`, 'score'));
    card.append(top, el('p', row.reason || 'No rationale supplied.'));
    const details = el('div', undefined, 'grid');
    details.append(fieldCard('Matched skills', ''), fieldCard('Gaps to explore', ''));
    details.children[0].append(list(row.matched_skills));
    details.children[1].append(list(row.missing_skills));
    card.append(details);
    if (row.evidence) card.append(el('blockquote', `"${row.evidence}"`));
    cards.append(card);
  });
  root.append(cards);
  const csv = button('Download CSV', 'ghost');
  csv.onclick = () => download(`/ranking/${state.job}/csv`);
  root.append(csv);
}
function renderQuestions(root) {
  renderGenerated(root, '/questions', 'questions', 'Create a structured phone screen.', data => {
    const wrap = el('div', undefined, 'question-list');
    (Array.isArray(data.questions) ? data.questions : []).forEach((item, i) => {
      const card = el('article', undefined, 'question-card');
      card.append(el('span', `${item.type || 'Question'} - ${i + 1}`, 'tag'), el('h3', item.question || 'Question'));
      card.append(el('p', `Good answer: ${item.good_answer || 'Look for specific, relevant evidence.'}`));
      wrap.append(card);
    });
    return wrap;
  });
}
function renderMarket(root) {
  const posts = el('textarea');
  posts.placeholder = 'Optional public job-post text or URLs...';
  renderGenerated(root, '/market', 'market', 'Paste public job posts for sourced results, or leave empty for estimates.', data => {
    const insights = Array.isArray(data.insights) ? data.insights : [];
    if (!insights.length) return el('p', 'No market data is available for this role yet.', 'notice');
    const section = el('section', undefined, 'market-results');
    section.append(el('p', `${insights.length} market signals found. Estimates are not verified.`), marketChart(insights));
    const table = el('table');
    table.setAttribute('aria-label', 'Market insights');
    const head = el('tr');
    ['Company', 'Experience', 'Compensation', 'Location', 'Source'].forEach(item => head.append(el('th', item)));
    table.append(el('thead'));
    table.querySelector('thead').append(head);
    const body = el('tbody');
    insights.forEach(item => {
      const row = el('tr');
      [item.company, item.experience_range, item.compensation_range_inr, item.hiring_location, item.source || 'Estimate']
        .forEach(value => row.append(el('td', value || 'Not stated')));
      body.append(row);
    });
    table.append(body);
    section.append(table);
    return section;
  }, posts);
}
function marketChart(insights) {
  const counts = {};
  insights.forEach(item => {
    const location = item.hiring_location || 'Unspecified';
    counts[location] = (counts[location] || 0) + 1;
  });
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 600 ${Math.max(120, entries.length * 44)}`);
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'Market signals grouped by hiring location');
  entries.forEach(([label, count], i) => {
    const y = i * 44 + 8;
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', '0'); text.setAttribute('y', String(y + 18)); text.textContent = label;
    const bar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    bar.setAttribute('x', '150'); bar.setAttribute('y', String(y)); bar.setAttribute('width', String(Math.max(24, count * 55))); bar.setAttribute('height', '24'); bar.setAttribute('rx', '8');
    const number = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    number.setAttribute('x', String(158 + count * 55)); number.setAttribute('y', String(y + 18)); number.textContent = String(count);
    svg.append(text, bar, number);
  });
  const figure = el('figure', undefined, 'market-chart');
  figure.append(svg, el('figcaption', 'Market signals grouped by hiring location. This is not a vacancy count.'));
  return figure;
}
function renderSearch(root) {
  renderGenerated(root, '/search', 'search', 'Create sourcing strings for Naukri and LinkedIn.', data => {
    const grid = el('div', undefined, 'search-grid');
    [['Naukri Boolean', data.naukri_boolean], ['Naukri plain', data.naukri_plain], ['LinkedIn Boolean', data.linkedin_boolean], ['LinkedIn plain', data.linkedin_plain]]
      .forEach(([title, value]) => {
        const card = el('article', undefined, 'search-card');
        card.append(el('h3', title), el('p', value || 'Not supplied.'));
        const copy = button('Copy', 'ghost');
        copy.onclick = async () => { await navigator.clipboard.writeText(value || ''); copy.textContent = 'Copied'; };
        card.append(copy); grid.append(card);
      });
    return grid;
  });
}
function renderGenerated(root, endpoint, key, description, format, extraInput = null) {
  const output = el('div'), generate = button('Generate');
  const run = async () => {
    if (!state.jd) { output.replaceChildren(el('p', 'Complete the job description first.', 'error')); return; }
    output.replaceChildren();
    const loader = createAILoader(key === 'questions' ? 'Generating interview questions...' : key === 'market' ? 'Preparing market insights...' : 'Building search strings...');
    output.append(loader.element);
    generate.disabled = true;
    try {
      const payload = {jd: state.jd};
      if (key === 'market' && extraInput) payload.posts = extraInput.value;
      const data = await request(endpoint, {method: 'POST', body: JSON.stringify(payload)});
      state.generated[key] = data;
      loader.complete('Ready to review');
      output.append(format(data));
    } catch (error) {
      loader.fail(error.message, run);
    } finally {
      generate.disabled = false;
    }
  };
  generate.onclick = run;
  root.append(el('p', description));
  if (extraInput) root.append(el('label', 'Public job-post text or URLs (optional)'), extraInput);
  root.append(generate, output);
  if (state.generated[key]) output.append(format(state.generated[key]));
  actions(root);
}
function render(root) {
  renderNav();
  root.replaceChildren(el('h2', labels[state.step]));
  if (state.step === 0) { root.append(el('p', 'We will start with the role, then build an evidence-based shortlist.'), nimoMessage('I will keep each step focused.')); actions(root); }
  if (state.step === 1) renderJD(root);
  if (state.step === 2) renderCVs(root);
  if (state.step === 3) renderRanking(root);
  if (state.step === 4) renderQuestions(root);
  if (state.step === 5) renderMarket(root);
  if (state.step === 6) renderSearch(root);
  if (state.step === 7) { root.append(el('p', 'You are ready to review, call, and collaborate on your shortlist.'), nimoMessage('Great work!')); actions(root, false); }
}
export function startSteps() { render(document.querySelector('#step-content')); }
