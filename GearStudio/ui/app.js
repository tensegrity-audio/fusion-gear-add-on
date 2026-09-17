(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const options = new URLSearchParams(window.location.search);
  const previewMode = options.get('preview') === '1' && options.get('host') !== 'fusion';
  const expectedHost = previewMode ? 'preview' : 'fusion';
  const state = { catalog: null, spec: null, presets: [], selection: null, mode: 'create', host: 'connecting', connected: false, supportedKinds: [], drafts: {}, parameterMaps: {}, valid: false, busy: false, request: 0, actions: {}, validationRequest: null, validationTimer: null, timeout: null };
  let connectionTimer, connectionDeadline;

  function transport() {
    if (previewMode) return window.gearStudioPreview && window.gearStudioPreview.send.bind(window.gearStudioPreview);
    if (window.adsk && typeof window.adsk.fusionSendData === 'function') return window.adsk.fusionSendData.bind(window.adsk);
    return null;
  }
  function startConnection() {
    clearTimeout(connectionTimer); clearTimeout(state.timeout); clearTimeout(state.validationTimer);
    state.connected = false; state.valid = false; state.host = 'connecting';
    connectionDeadline = Date.now() + 15000;
    $('host-label').textContent = previewMode ? 'Loading interface preview' : 'Connecting to Fusion';
    $('retry-connection').hidden = true;
    setFooter(previewMode ? 'Loading interface preview' : 'Connecting to Fusion', 'Waiting for the panel connection.', 'checking');
    renderActions();
    function poll() {
      if (state.connected) return;
      if (Date.now() >= connectionDeadline) {
        state.host = 'disconnected';
        $('host-label').textContent = 'Not connected';
        $('retry-connection').hidden = false;
        setFooter('Connection unavailable', previewMode ? 'Reload the locally served interface preview.' : 'Open Gear Studio from Scripts and Add-Ins in Fusion, then retry the connection.', 'error');
        renderActions();
        return;
      }
      // Only the read-only handshake is retried. Never replay build or edit actions.
      if (transport()) send('ready');
      if (!state.connected) connectionTimer = setTimeout(poll, 500);
    }
    poll();
  }
  const groups = [
    { label: 'EXTERNAL GEARS', ids: ['spur', 'helical', 'herringbone'] },
    { label: 'INTERNAL GEARS', ids: ['internal_spur', 'internal_helical', 'internal_herringbone'] },
    { label: 'LINEAR MOTION', ids: ['rack', 'helical_rack'] },
    { label: 'INTERSECTING & SKEW AXES', ids: ['worm', 'worm_wheel', 'bevel', 'spiral_bevel', 'crown'] }
  ];
  const metricLabels = {
    pitch_diameter: ['Pitch diameter', 'mm'], base_diameter: ['Base diameter', 'mm'], tip_diameter: ['Tip diameter', 'mm'], root_diameter: ['Root diameter', 'mm'], tooth_thickness: ['Reference tooth thickness', 'mm'], transverse_module: ['Transverse module', 'mm'], transverse_pressure_angle: ['Transverse pressure angle', '°'], min_teeth_without_undercut: ['Undercut threshold', 'teeth'], estimated_sections: ['Profile sections', ''], ring_rim: ['Ring rim thickness', 'mm'], rack_length: ['Rack length', 'mm'], lead: ['Lead', 'mm'], pitch_cone_angle: ['Pitch cone angle', '°'], cone_distance: ['Cone distance', 'mm'], outside_diameter: ['Outside diameter', 'mm'], root_radius: ['Root radius', 'mm'], pitch_radius: ['Pitch radius', 'mm'], centre_distance: ['Nominal centre distance', 'mm'], center_distance: ['Nominal center distance', 'mm']
  };

  function send(action, payload) {
    const requestId = 'gs-' + (++state.request);
    state.actions[requestId] = action;
    if (state.request > 200) delete state.actions['gs-' + (state.request - 200)];
    const data = Object.assign({ requestId }, payload || {});
    try {
      if (action !== 'ready' && !state.connected) throw new Error('Wait for the Fusion connection before using this action.');
      const deliver = transport();
      if (!deliver) throw new Error('The Fusion connection is unavailable.');
      const pending = deliver(action, JSON.stringify(data));
      if (pending && typeof pending.catch === 'function') pending.catch((error) => { if (action !== 'ready') showError(error.message || String(error)); });
    } catch (error) { if (action !== 'ready') showError(error.message || String(error)); }
    return requestId;
  }
  function familyFor(kind) { return state.catalog && state.catalog.families.find((f) => f.id === kind); }
  function defaultSpec(kind) {
    const family = familyFor(kind);
    const parameters = {};
    family.fields.forEach((key) => { parameters[key] = String(Object.prototype.hasOwnProperty.call(family.defaults || {}, key) ? family.defaults[key] : state.catalog.fields[key].default); });
    return { schema_version: 1, kind, name: family.label + (family.label.toLowerCase().includes('gear') ? '' : ' gear'), parameters, placement: {} };
  }
  function icon(kind) {
    const rack = '<path d="M2 16h20M2 16V9h3l1-5h3l1 5h4l1-5h3l1 5h3v7"/>';
    const base = '<path d="m10 2 4 0 .5 3 2 1 2.8-1 2 3.5-2.2 2 .1 2.7 2.1 2-2 3.5-2.8-1-2 1-.5 3h-4l-.5-3-2-1-2.8 1-2-3.5 2.1-2 .1-2.7-2.2-2L4.7 5l2.8 1 2-1Z"/><circle cx="12" cy="12" r="3.4"/>';
    let content = base;
    if (kind.includes('rack')) content = rack;
    else if (kind.startsWith('internal')) content = '<circle cx="12" cy="12" r="9.8"/><path d="m10 5 4 0 .4 2 1.5.8 1.9-.5 1.2 2-1.5 1.4v1.7l1.5 1.4-1.2 2-1.9-.5-1.5.8-.4 2h-4l-.4-2-1.5-.8-1.9.5-1.2-2 1.5-1.4v-1.7L5 9.8l1.2-2 1.9.5 1.5-.8Z"/>';
    else if (kind === 'worm') content = '<path d="M4 5v14M20 5v14M3 7h18M3 17h18M5 17 9 7M10 17l4-10M15 17l4-10"/>';
    else if (kind.includes('bevel')) content = '<path d="m3 17 6-11h6l6 11-5 3H8Z"/><path d="m9 6-1 14m7-14 1 14M3 17h18M12 6v14"/>';
    else if (kind === 'crown') content = '<ellipse cx="12" cy="16" rx="10" ry="5"/><path d="M2 16V9l3 2V6l4 3V4h6v5l4-3v5l3-2v7"/>';
    return '<svg viewBox="0 0 24 24" aria-hidden="true">' + content + '</svg>';
  }
  function renderFamilies() {
    const list = $('family-list'); list.replaceChildren();
    const known = new Set();
    function addGroup(label, families) {
      if (!families.length) return;
      const block = document.createElement('div'); block.className = 'family-group';
      const title = document.createElement('div'); title.className = 'family-group-label'; title.textContent = label; block.appendChild(title);
      families.forEach((family) => {
        known.add(family.id);
        const button = document.createElement('button'); button.type = 'button'; button.className = 'family-button' + (state.spec.kind === family.id ? ' active' : ''); button.dataset.kind = family.id;
        button.setAttribute('aria-pressed', String(state.spec.kind === family.id));
        button.innerHTML = icon(family.id);
        const labelNode = document.createElement('span'); labelNode.className = 'family-label'; labelNode.textContent = family.label;
        const supported = state.supportedKinds.includes(family.id);
        if (!supported) { const unavailable = document.createElement('span'); unavailable.className = 'unavailable-label'; unavailable.textContent = 'Not available in this build'; labelNode.appendChild(unavailable); }
        button.appendChild(labelNode); button.disabled = !supported || state.busy;
        button.title = family.description + (!supported ? ' This family is not available in this build.' : '');
        button.addEventListener('click', () => switchFamily(family.id)); block.appendChild(button);
      }); list.appendChild(block);
    }
    groups.forEach((group) => addGroup(group.label, group.ids.map(familyFor).filter(Boolean)));
    addGroup('OTHER GEARS', state.catalog.families.filter((family) => !known.has(family.id)));
    $('family-count').textContent = String(state.supportedKinds.length).padStart(2, '0');
  }
  function switchFamily(kind) {
    if (state.busy || state.spec.kind === kind) return;
    state.drafts[state.spec.kind] = clone(state.spec);
    const draft = state.drafts[kind];
    if (draft) { state.spec = clone(draft); state.mode = state.spec.id ? 'edit' : 'create'; renderConfiguration(); scheduleValidation(0); }
    else { state.spec = defaultSpec(kind); state.mode = 'create'; renderConfiguration(); scheduleValidation(0); send('loadLast', { kind }); }
  }
  function fieldMetadata(key, family) { return Object.assign({}, state.catalog.fields[key], (family.fieldOverrides || {})[key] || {}); }
  function renderField(key, family) {
    const meta = fieldMetadata(key, family);
    const field = document.createElement('div'); field.className = 'field'; field.dataset.field = key;
    const labelRow = document.createElement('div'); labelRow.className = 'field-label-row';
    const label = document.createElement('label'); label.htmlFor = 'field-' + key; label.textContent = meta.label;
    if (key === 'module' && family.moduleConvention === 'outer normal') label.textContent = 'Outer normal module';
    labelRow.appendChild(label);
    if (meta.description) { const tip = document.createElement('span'); tip.className = 'info-tip'; tip.textContent = 'i'; tip.title = meta.description; tip.tabIndex = 0; tip.setAttribute('aria-label', meta.description); labelRow.appendChild(tip); }
    field.appendChild(labelRow);
    const wrap = document.createElement('div'); wrap.className = 'input-wrap';
    const input = document.createElement('input'); input.type = 'text'; input.id = 'field-' + key; input.name = key; input.autocomplete = 'off'; input.spellcheck = false; input.value = state.spec.parameters[key] == null ? meta.default : state.spec.parameters[key]; input.setAttribute('aria-describedby', 'message-' + key + ' description-' + key); input.disabled = state.busy;
    const names = state.parameterMaps[state.spec.id] || {};
    if (names[key]) input.title = 'Fusion parameter: ' + names[key];
    input.addEventListener('input', () => { state.spec.parameters[key] = input.value; scheduleValidation(); }); wrap.appendChild(input);
    if (meta.unit) { const unit = document.createElement('span'); unit.className = 'input-unit'; unit.textContent = meta.unit === 'deg' ? '°' : meta.unit; wrap.appendChild(unit); }
    field.appendChild(wrap);
    const description = document.createElement('span'); description.id = 'description-' + key; description.className = 'field-description';
    if (key === 'module') description.textContent = family.moduleConvention === 'outer normal' ? 'Tooth size at the outer normal section.' : 'Tooth size in the normal plane.';
    else if (key === 'teeth' || key === 'worm_starts' || key === 'mate_teeth') description.textContent = 'Whole number or integer expression.';
    else if (key === 'backlash') description.textContent = 'Reduction on this gear, in the normal plane.';
    else if (key === 'helix_angle' || key === 'spiral_angle') description.textContent = 'Change the sign to reverse the hand.';
    else if (key === 'bore') description.textContent = 'Use 0 mm for a solid centre.';
    else description.textContent = meta.description || '';
    if (description.textContent.length > 100) description.textContent = description.textContent.slice(0, 97) + '…';
    field.appendChild(description);
    const message = document.createElement('p'); message.id = 'message-' + key; message.className = 'field-message'; message.hidden = true; field.appendChild(message);
    return field;
  }
  function renderConfiguration() {
    if (!state.spec || !state.catalog) return;
    const family = familyFor(state.spec.kind); if (!family) return;
    renderFamilies();
    $('family-title').textContent = family.label + (family.label.toLowerCase().includes('gear') || family.id.includes('rack') || family.id === 'worm' || family.id === 'worm_wheel' ? '' : ' gear');
    $('family-description').textContent = family.description;
    $('configuration-mode').textContent = state.mode === 'edit' ? 'EDIT CONFIGURATION' : 'NEW CONFIGURATION';
    $('mode-chip').textContent = state.mode === 'edit' ? 'EDIT' : 'CREATE';
    $('gear-name').value = state.spec.name || '';
    const names = state.parameterMaps[state.spec.id];
    $('parameter-name-help').textContent = names && Object.keys(names).length ? 'This gear: ' + Object.values(names).slice(0, 3).join(' · ') + '. Hover over an input to see its parameter name.' : 'Names start with the setting: Module_G1, Teeth_G1, Bore_G1. Each gear gets its own G-number.';
    $('preview-title').textContent = family.id.includes('rack') ? 'Rack section' : family.id === 'worm' || family.id.includes('bevel') ? 'Side envelope' : family.id === 'crown' ? 'Face envelope' : family.id === 'worm_wheel' ? 'Axial envelope' : 'Axial profile';
    document.querySelector('.canvas-origin').textContent = family.id === 'worm' || family.id.includes('bevel') ? 'SIDE' : 'XY';
    const sections = $('parameter-sections'); sections.replaceChildren();
    const grouped = {};
    family.fields.forEach((key) => { const group = fieldMetadata(key, family).group || 'Tooth system'; (grouped[group] || (grouped[group] = [])).push(key); });
    let number = 1;
    ['Tooth system', 'Body', 'Pair geometry', ...Object.keys(grouped).filter((group) => !['Tooth system', 'Body', 'Pair geometry', 'Advanced'].includes(group)), 'Advanced'].forEach((group) => {
      if (!grouped[group]) return;
      const advanced = group === 'Advanced';
      const section = document.createElement(advanced ? 'details' : 'section'); section.className = advanced ? 'advanced-section' : 'parameter-section';
      const heading = document.createElement(advanced ? 'summary' : 'h2'); heading.className = advanced ? '' : 'section-title'; heading.textContent = { 'Tooth system': 'Tooth geometry', Body: 'Body & fit', 'Pair geometry': 'Mating geometry', Advanced: 'Advanced tooth geometry' }[group] || group;
      if (!advanced) { const counter = document.createElement('span'); counter.className = 'section-number'; counter.textContent = String(number++).padStart(2, '0'); heading.appendChild(counter); }
      section.appendChild(heading);
      const grid = document.createElement('div'); grid.className = 'field-grid'; grouped[group].forEach((key) => grid.appendChild(renderField(key, family))); section.appendChild(grid); sections.appendChild(section);
    });
    state.valid = false; clearPreview('Checking your configuration'); renderActions(); renderSelection();
  }
  function renderPresets() {
    const list = $('preset-list'); list.replaceChildren();
    if (!state.presets.length) { const empty = document.createElement('p'); empty.className = 'preset-empty'; empty.textContent = 'Keep your go-to configurations here.'; list.appendChild(empty); return; }
    state.presets.forEach((preset) => {
      const row = document.createElement('div'); row.className = 'preset-row';
      const load = document.createElement('button'); load.className = 'preset-load'; load.textContent = preset.name; load.title = 'Load ' + preset.name; load.disabled = state.busy; load.addEventListener('click', () => { if (state.spec) state.drafts[state.spec.kind] = clone(state.spec); send('loadPreset', { id: preset.id }); });
      const remove = document.createElement('button'); remove.className = 'preset-delete'; remove.textContent = '×'; remove.setAttribute('aria-label', 'Delete preset ' + preset.name); remove.title = 'Delete this preset'; remove.disabled = state.busy; remove.addEventListener('click', () => send('deletePreset', { id: preset.id })); row.append(load, remove); list.appendChild(row);
    });
  }
  function renderSelection() {
    const selected = state.selection;
    $('selection-name').textContent = selected ? selected.name || 'Selected gear' : 'No managed gear selected';
    $('selection-help').textContent = selected ? selected.stale ? 'Parameters changed. Use Update from Parameters to rebuild.' : 'Existing definition available for editing or duplication.' : 'Select a Gear Studio body or component in Fusion to edit it.';
    $('selection-dot').classList.toggle('selected', Boolean(selected));
    $('selection-dot').classList.toggle('stale', Boolean(selected && selected.stale));
    $('parameter-upgrade').hidden = !selected || selected.readableParameterNames !== false;
    $('rename-parameters').disabled = !selected || selected.readableParameterNames !== false || state.busy || !state.connected || state.host !== 'fusion';
    ['edit-selected', 'duplicate-selected', 'update-selected'].forEach((id) => { $(id).disabled = !selected || state.busy || !state.connected || state.host !== 'fusion'; });
  }
  function renderActions() {
    const supported = Boolean(state.spec && state.supportedKinds.includes(state.spec.kind));
    $('build-gear').disabled = !state.valid || state.busy || !supported || !state.connected || state.host !== 'fusion';
    $('build-label').textContent = state.busy ? 'Working in Fusion' : state.mode === 'edit' ? 'Update gear' : 'Create gear';
    $('save-preset').disabled = !state.valid || state.busy || !state.connected;
    $('new-gear').disabled = state.busy || !state.spec || !state.connected;
    $('load-last').disabled = state.busy || !state.spec || !state.connected;
    $('refresh-selection').disabled = state.busy || !state.connected || state.host !== 'fusion';
    $('open-parameters').disabled = state.busy || !state.connected || state.host !== 'fusion';
    $('cancel-build').hidden = !state.busy;
    $('progress-wrap').hidden = !state.busy;
    $('gear-name').disabled = state.busy || !state.connected;
    renderSelection();
  }
  function scheduleValidation(delay) {
    state.valid = false; state.validationRequest = null;
    clearTimeout(state.validationTimer); clearTimeout(state.timeout);
    $('validation-title').textContent = 'Checking configuration'; $('validation-indicator').className = 'status-indicator checking';
    $('preview-canvas').classList.add('pending');
    setFooter('Checking configuration', 'No geometry is built while you type.', 'checking'); renderActions();
    state.validationTimer = setTimeout(() => {
      if (!state.spec || state.busy) return;
      // Reserve the ID before sending: a test or local bridge may reply synchronously.
      state.validationRequest = 'gs-' + (state.request + 1);
      state.timeout = setTimeout(() => {
        state.valid = false;
        $('validation-title').textContent = 'Waiting for Fusion';
        $('validation-summary').textContent = 'Validation has not returned. Check Fusion for an open dialog, then edit a field to retry.';
        setFooter('Waiting for validation', 'Check Fusion for an open dialog.', 'warning'); renderActions();
      }, 15000);
      send('validate', { spec: clone(state.spec) });
    }, delay == null ? 240 : delay);
  }
  function setFooter(title, detail, status) { $('footer-status').textContent = title; $('footer-detail').textContent = detail || ''; $('footer-dot').className = 'status-indicator ' + (status || ''); }
  function displayValidation(data) {
    if (data.requestId !== state.validationRequest || state.busy) return;
    clearTimeout(state.timeout);
    $('preview-canvas').classList.remove('pending');
    state.valid = Boolean(data.valid);
    document.querySelectorAll('.field').forEach((field) => { field.classList.remove('invalid', 'warning'); const input = field.querySelector('input'); input.removeAttribute('aria-invalid'); const message = field.querySelector('.field-message'); message.hidden = true; message.textContent = ''; });
    const issues = Array.isArray(data.issues) ? data.issues : [];
    const errors = issues.filter((issue) => issue.severity === 'error');
    const warnings = issues.filter((issue) => issue.severity !== 'error');
    const right = $('validation-issues'); right.replaceChildren();
    issues.forEach((issue) => {
      const input = typeof issue.field === 'string' ? $('field-' + issue.field) : null;
      if (input) {
        const field = input.closest('.field'); const message = field.querySelector('.field-message');
        field.classList.add(issue.severity === 'error' ? 'invalid' : 'warning');
        if (issue.severity === 'error') { input.setAttribute('aria-invalid', 'true'); const advanced = field.closest('details'); if (advanced) advanced.open = true; }
        message.textContent += (message.textContent ? ' ' : '') + issue.message; message.hidden = false;
      }
      if (!input || issue.severity !== 'error') { const item = document.createElement('div'); item.className = 'validation-issue' + (issue.severity === 'error' ? ' error' : ''); item.textContent = issue.message; right.appendChild(item); }
    });
    const title = !state.valid ? 'Configuration needs attention' : warnings.length ? 'Ready with notes' : 'Geometry checks passed';
    $('validation-title').textContent = title; $('validation-indicator').className = 'status-indicator ' + (!state.valid ? 'error' : warnings.length ? 'warning' : '');
    $('validation-summary').textContent = !state.valid ? errors.length ? 'Review the highlighted inputs before creating a solid.' : 'Adjust the configuration or review the notes above.' : 'Input and profile checks passed. Mating-gear compatibility still requires an assembly check.';
    const cost = data.cost || {};
    const costParts = [];
    if (Number.isFinite(cost.estimated_sections)) costParts.push(cost.estimated_sections + ' profile sections');
    if (Number.isFinite(cost.points)) costParts.push(cost.points + ' profile points');
    if (Number.isFinite(cost.estimated_points)) costParts.push(cost.estimated_points + ' profile points');
    if (cost.level) costParts.push('Build complexity: ' + cost.level);
    $('cost-summary').hidden = !costParts.length; $('cost-summary').textContent = costParts.join(' · ');
    renderMetrics(data.metrics || {});
    if (data.preview && data.preview.paths && data.preview.paths.length) renderPreview(data.preview); else clearPreview(state.valid ? 'Section preview unavailable' : 'A valid section is needed to preview');
    if (state.host === 'preview') setFooter('Interface preview', 'Native B-rep creation is available inside Fusion.', state.valid ? '' : 'warning');
    else setFooter(state.valid ? state.mode === 'edit' ? 'Ready to update' : 'Ready to create' : 'Check your inputs', state.valid ? 'Validated configuration · Native B-rep solid' : 'The last successful solid stays in place.', state.valid ? warnings.length ? 'warning' : '' : 'error');
    renderActions();
  }
  function renderMetrics(metrics) {
    const container = $('metrics-grid'); container.replaceChildren();
    const priority = ['pitch_diameter', 'tip_diameter', 'root_diameter', 'tooth_thickness', 'ring_rim', 'rack_length', 'lead', 'pitch_cone_angle', 'cone_distance', 'transverse_module', 'transverse_pressure_angle', 'min_teeth_without_undercut'];
    const keys = [...priority.filter((key) => Object.prototype.hasOwnProperty.call(metrics, key)), ...Object.keys(metrics).filter((key) => !priority.includes(key) && key !== 'estimated_sections')].slice(0, 8);
    if (!keys.length) { const empty = document.createElement('div'); empty.className = 'metric'; const label = document.createElement('span'); label.textContent = 'Valid inputs required'; empty.appendChild(label); container.appendChild(empty); return; }
    keys.forEach((key) => {
      const info = metrics[key]; const object = typeof info === 'object' && info !== null;
      const value = object ? info.value : info;
      if (typeof value !== 'number' || !Number.isFinite(value)) return;
      const known = metricLabels[key] || [key.replace(/_/g, ' ').replace(/^./, (letter) => letter.toUpperCase()), ''];
      const label = object && info.label ? info.label : known[0]; const unit = object && info.unit != null ? info.unit : known[1];
      const item = document.createElement('div'); item.className = 'metric';
      const name = document.createElement('span'); name.textContent = label;
      const result = document.createElement('strong'); result.textContent = unit === 'teeth' ? value.toFixed(1) : value.toFixed(2);
      if (unit) { const suffix = document.createElement('small'); suffix.textContent = unit; result.appendChild(suffix); }
      item.append(name, result); container.appendChild(item);
    });
  }
  function svgNode(tag, attributes) { const node = document.createElementNS('http://www.w3.org/2000/svg', tag); Object.keys(attributes).forEach((name) => node.setAttribute(name, attributes[name])); return node; }
  function renderPreview(preview) {
    const bounds = preview.bounds;
    if (!Array.isArray(bounds) || bounds.length !== 4 || !bounds.every(Number.isFinite)) { clearPreview('Section preview unavailable'); return; }
    const width = bounds[2] - bounds[0], height = bounds[3] - bounds[1];
    if (width <= 0 || height <= 0) { clearPreview('Section preview unavailable'); return; }
    const padding = Math.max(width, height) * .07;
    $('gear-preview').setAttribute('viewBox', [bounds[0] - padding, -bounds[3] - padding, width + 2 * padding, height + 2 * padding].join(' '));
    const drawing = $('preview-drawing'); drawing.replaceChildren();
    drawing.appendChild(svgNode('line', { x1: bounds[0] - padding, y1: 0, x2: bounds[2] + padding, y2: 0, class: 'preview-centerline' }));
    drawing.appendChild(svgNode('line', { x1: 0, y1: bounds[1] - padding, x2: 0, y2: bounds[3] + padding, class: 'preview-centerline' }));
    let outline = ''; const extra = [];
    (preview.paths || []).forEach((path) => {
      if (!Array.isArray(path.points) || path.points.length < 2 || path.points.length > 50000) return;
      if (path.points.some((point) => !Array.isArray(point) || !Number.isFinite(point[0]) || !Number.isFinite(point[1]))) return;
      const d = path.points.map((point, i) => (i ? 'L' : 'M') + point[0] + ',' + point[1]).join(' ') + (path.closed ? 'Z' : '');
      if ((path.role === 'outline' || path.role === 'cutout' || !path.role) && path.closed) outline += d + ' ';
      else extra.push(svgNode('path', { d, class: path.role === 'construction' ? 'preview-construction' : 'preview-detail' }));
    });
    if (outline) drawing.appendChild(svgNode('path', { d: outline, class: 'preview-outline', 'fill-rule': 'evenodd' }));
    extra.forEach((node) => drawing.appendChild(node));
    $('preview-placeholder').hidden = true;
    $('preview-scale').textContent = width.toFixed(2) + ' × ' + height.toFixed(2) + ' mm';
    let caption = preview.label || preview.description || preview.note || preview.caption || 'Calculated section. The generated result is a B-rep solid.';
    if (Array.isArray(preview.notes) && preview.notes.length) caption = preview.notes.join(' ');
    $('preview-caption').textContent = caption;
  }
  function clearPreview(message) { $('preview-drawing').replaceChildren(); $('preview-placeholder').hidden = false; $('preview-placeholder').lastElementChild.textContent = message; $('preview-scale').textContent = ''; }
  function setBusy(busy) {
    state.busy = busy;
    if (busy) { clearTimeout(state.validationTimer); clearTimeout(state.timeout); state.validationRequest = null; $('cancel-build').disabled = false; $('cancel-build').textContent = 'Cancel build'; $('progress-bar').style.width = '0%'; $('progress-percent').textContent = '0%'; setFooter('Preparing geometry', 'Fusion will validate before creating a candidate solid.', 'busy'); }
    document.querySelectorAll('#gear-form input').forEach((input) => { input.disabled = busy; });
    if (state.catalog && state.spec) renderFamilies(); renderPresets(); renderActions();
  }
  let toastTimer;
  function toast(message, error) { clearTimeout(toastTimer); $('toast').textContent = message; $('toast').className = 'toast' + (error ? ' error' : ''); $('toast').hidden = false; toastTimer = setTimeout(() => { $('toast').hidden = true; }, error ? 11000 : 6000); }
  function showError(message) { clearTimeout(state.timeout); setBusy(false); state.valid = false; renderActions(); setFooter('Action could not finish', message, 'error'); toast(message, true); }
  function applyState(data) {
    // A native panel can never be downgraded to the browser adapter. Ignore
    // late duplicate ready replies so they cannot reset an edit or active build.
    if (data.host !== expectedHost || state.host === 'disconnected' || !transport()) return;
    if (state.connected && data.requestId && state.actions[data.requestId] === 'ready') return;
    if (!data.catalog || !data.spec) throw new Error('The panel connection returned an incomplete configuration.');
    state.connected = true; clearTimeout(connectionTimer);
    $('retry-connection').hidden = true;
    if (data.catalog) state.catalog = data.catalog;
    if (data.supportedKinds) state.supportedKinds = data.supportedKinds;
    if (data.host) state.host = data.host;
    if (Object.prototype.hasOwnProperty.call(data, 'selection')) state.selection = data.selection;
    if (data.presets) state.presets = data.presets;
    if (data.spec) state.spec = clone(data.spec);
    if (data.spec && data.spec.id && data.parameterNames) state.parameterMaps[data.spec.id] = clone(data.parameterNames);
    if (data.version) $('installed-version').textContent = 'Gear Studio ' + data.version;
    if (data.installationPath) $('installed-path').textContent = data.installationPath;
    if (data.mode) state.mode = data.mode;
    else if (data.spec) state.mode = data.spec.id ? 'edit' : 'create';
    $('host-label').textContent = state.host === 'preview' ? 'Interface preview' : 'Autodesk Fusion';
    $('preview-notice').hidden = state.host !== 'preview';
    if (!state.spec && state.catalog) state.spec = defaultSpec(state.supportedKinds[0] || 'spur');
    setBusy(false); renderConfiguration(); renderPresets(); scheduleValidation(0);
  }
  window.fusionJavaScriptHandler = {
    handle: function (action, jsonString) {
      try {
        const data = typeof jsonString === 'string' ? JSON.parse(jsonString || '{}') : jsonString;
        if (action === 'state') applyState(data);
        else if (action === 'validation') displayValidation(data);
        else if (action === 'selection') { state.selection = data && Object.prototype.hasOwnProperty.call(data, 'selection') ? data.selection : data; renderSelection(); }
        else if (action === 'progress') { if (!state.busy) setBusy(true); const percent = Math.max(0, Math.min(100, Number(data.percent) || 0)); $('progress-bar').style.width = percent + '%'; $('progress-percent').textContent = Math.round(percent) + '%'; $('cancel-build').disabled = data.cancellable === false; setFooter(data.message || 'Building candidate solid', 'The existing gear stays in place until the build succeeds.', 'busy'); }
        else if (action === 'result') {
          const wasBusy = state.busy; setBusy(false);
          if (data.presets) { state.presets = data.presets; renderPresets(); }
          if (data.ok) {
            if (data.renamedAliases) {
              // Native renaming also updates expression references. Keep unsaved
              // form/family drafts in step without replacing them with table values.
              const rewrite = (expression) => expression.replace(/[\p{L}_$][\p{L}\p{N}_$°"]*/gu, (name) => data.renamedAliases[name] || name);
              [state.spec, ...Object.values(state.drafts)].filter(Boolean).forEach((spec) => {
                Object.keys(spec.parameters).forEach((field) => { spec.parameters[field] = rewrite(spec.parameters[field]); });
              });
            }
            const gearId = data.gearId || (data.spec && data.spec.id);
            if (gearId && data.parameterNames) state.parameterMaps[gearId] = clone(data.parameterNames);
            if (Object.prototype.hasOwnProperty.call(data, 'selection')) state.selection = data.selection;
            if (data.spec) { state.spec = clone(data.spec); state.mode = data.mode || (data.spec.id ? 'edit' : 'create'); renderConfiguration(); scheduleValidation(0); }
            else if (wasBusy) { renderConfiguration(); scheduleValidation(0); }
            if (data.message) toast(data.message, false);
          } else { showError(data.message || 'The action did not finish.'); }
        }
        else if (action === 'error') { if (data.requestId && state.actions[data.requestId] === 'validate' && data.requestId !== state.validationRequest && !state.busy) return 'OK'; showError(data.message || 'The action could not finish.'); }
      } catch (error) { showError('Could not read the Fusion response: ' + error.message); }
      return 'OK';
    }
  };

  $('gear-name').addEventListener('input', () => { if (state.spec) { state.spec.name = $('gear-name').value; scheduleValidation(); } });
  $('gear-form').addEventListener('submit', (event) => { event.preventDefault(); if (!$('build-gear').disabled) $('build-gear').click(); });
  $('build-gear').addEventListener('click', () => { if (!state.connected || !state.valid || state.busy || state.host !== 'fusion') return; const spec = clone(state.spec); setBusy(true); send('build', { spec }); });
  $('cancel-build').addEventListener('click', () => { $('cancel-build').disabled = true; $('cancel-build').textContent = 'Cancelling…'; setFooter('Cancellation requested', 'Fusion can stop between modeling operations.', 'busy'); send('cancel'); });
  $('new-gear').addEventListener('click', () => { if (!state.spec || state.busy) return; state.drafts[state.spec.kind] = clone(state.spec); state.spec = defaultSpec(state.spec.kind); state.mode = 'create'; renderConfiguration(); scheduleValidation(0); send('loadLast', { kind: state.spec.kind }); });
  $('load-last').addEventListener('click', () => { if (state.spec && !state.busy) send('loadLast', { kind: state.spec.kind }); });
  $('refresh-selection').addEventListener('click', () => send('refreshSelection'));
  $('edit-selected').addEventListener('click', () => send('editSelected'));
  $('duplicate-selected').addEventListener('click', () => send('duplicateSelected'));
  $('update-selected').addEventListener('click', () => { if (state.selection && !state.busy) { setBusy(true); send('updateSelected'); } });
  $('open-parameters').addEventListener('click', () => send('openParameters'));
  $('rename-parameters').addEventListener('click', () => {
    if ($('rename-parameters').disabled) return;
    setBusy(true); $('cancel-build').disabled = true;
    setFooter('Renaming parameters', 'Keeping the current gear geometry and expression references.', 'busy');
    send('renameParameters');
  });
  $('open-guide').addEventListener('click', () => $('guide-dialog').showModal());
  $('close-guide').addEventListener('click', () => $('guide-dialog').close());
  $('save-preset').addEventListener('click', () => { if (!state.valid || state.busy) return; $('preset-name').value = state.spec.name || ''; $('preset-dialog').showModal(); $('preset-name').focus(); $('preset-name').select(); });
  $('dismiss-preset').addEventListener('click', () => $('preset-dialog').close());
  $('preset-form').addEventListener('submit', (event) => { event.preventDefault(); const name = $('preset-name').value.trim(); if (!name || !state.valid) return; $('preset-dialog').close(); send('savePreset', { name, spec: clone(state.spec) }); });
  $('preset-dialog').addEventListener('click', (event) => { if (event.target === $('preset-dialog')) { const bounds = $('preset-dialog').getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) $('preset-dialog').close(); } });
  $('retry-connection').addEventListener('click', startConnection);
  startConnection();
}());
