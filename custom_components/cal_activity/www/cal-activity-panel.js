class CalActivityPanel extends HTMLElement {
  constructor() {
    super();
    // A real shadow root is required for the `:host` selector below (and for
    // our plain `button`/`input`/`select`/`h1`/`*` rules) to actually stay
    // scoped to this panel. Without one, that <style> tag is just a normal
    // light-DOM stylesheet: `:host` matches nothing (so our own sizing rules
    // silently no-op) while the generic tag/class selectors leak out and
    // apply to the rest of the Home Assistant UI.
    this.attachShadow({ mode: "open" });
    this._entries = [];
    this._calendars = [];
    this._initialized = false;
    this._activeKey = "__new__"; // entry_id, or "__new__" for the create-new sub-tab
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._initialized) {
      this._initialized = true;
      this._boot();
    }
  }

  get hass() {
    return this._hass;
  }

  async _boot() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; box-sizing: border-box; min-height: 100%; padding: 16px;
          max-width: 960px; margin: 0 auto;
          font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); }
        *, *::before, *::after { box-sizing: border-box; }
        h1 { font-size: 24px; font-weight: 400; color: var(--primary-text-color); margin: 4px 0 4px 0;
          display: flex; align-items: center; gap: 10px; }
        h1 ha-icon { --mdc-icon-size: 28px; color: var(--primary-color); }
        p.subtitle { color: var(--secondary-text-color); margin-top: 0; margin-bottom: 20px; }
        .cc-subtabs { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
        .cc-subtab { display: flex; align-items: center; gap: 6px; padding: 6px 14px; cursor: pointer;
          background: var(--secondary-background-color, #eee); border: 1px solid transparent; border-radius: 999px;
          font-size: 13px; color: var(--primary-text-color); }
        .cc-subtab.active { background: var(--primary-color); color: var(--text-primary-color, white); }
        .cc-subtab-new { background: transparent; border: 1px dashed var(--divider-color, #ccc);
          color: var(--secondary-text-color); }
        .cc-subtab-new.active { background: var(--primary-color); color: var(--text-primary-color, white);
          border-style: solid; }
        .cc-subtab ha-icon { --mdc-icon-size: 16px; }
        .cc-render-error { color: var(--error-color, #db4437); background: rgba(219,68,55,0.08);
          border: 1px solid var(--error-color, #db4437); border-radius: 8px; padding: 12px; margin-bottom: 16px;
          font-size: 13px; white-space: pre-wrap; }
        .cc-card {
          background: var(--card-background-color, white);
          border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,0.1));
          padding: 16px; margin-bottom: 16px; border: 1px solid var(--ha-card-border-color, transparent);
        }
        .cc-card-header { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
        .cc-card-header ha-icon { --mdc-icon-size: 24px; color: var(--primary-color); flex-shrink: 0; }
        .cc-card-header img.cc-avatar { width: 28px; height: 28px; border-radius: 50%; object-fit: cover;
          flex-shrink: 0; }
        .cc-card-header input[type="text"].cc-name { font-size: 16px; font-weight: 500; flex: 1; }
        .cc-section-title { font-weight: 500; font-size: 13px; text-transform: uppercase;
          letter-spacing: .03em; color: var(--secondary-text-color); margin: 16px 0 6px 0; }
        .cc-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 8px; }
        input[type="text"], select {
          padding: 8px 10px; border-radius: 6px; min-width: 160px;
          border: 1px solid var(--divider-color, #ccc); background: var(--card-background-color);
          color: var(--primary-text-color); font-size: 14px; box-sizing: border-box;
        }
        input[type="text"] { flex: 1; }
        .cc-actions { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
        button {
          border: none; border-radius: 6px; padding: 8px 14px; font-size: 14px; cursor: pointer;
          background: var(--primary-color); color: var(--text-primary-color, white);
        }
        button.secondary { background: transparent; color: var(--primary-color);
          border: 1px solid var(--primary-color); }
        button.danger { background: var(--error-color, #db4437); color: white; }
        button:disabled { opacity: .4; cursor: default; }
        .cc-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
        .cc-chip { display: inline-flex; align-items: center; gap: 4px; background: var(--secondary-background-color, #eee);
          border-radius: 999px; padding: 4px 6px 4px 10px; font-size: 13px; color: var(--primary-text-color); }
        .cc-chip-remove { background: none; border: none; color: var(--secondary-text-color); cursor: pointer;
          font-size: 15px; line-height: 1; padding: 2px 4px; border-radius: 50%; }
        .cc-chip-remove:hover { background: rgba(0,0,0,0.1); }
        .cc-chip-empty { font-size: 13px; color: var(--secondary-text-color); font-style: italic; }
        .cc-icon-picker .cc-row ha-icon { --mdc-icon-size: 22px; color: var(--primary-text-color); }
        .cc-picture-preview { width: 40px; height: 40px; border-radius: 6px; object-fit: cover; display: none; }
        .cc-picture-status { display: block; font-size: 12px; color: var(--secondary-text-color); margin-top: 4px; }
        .cc-filter-fields { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; padding: 8px;
          background: var(--secondary-background-color, #f4f4f4); border-radius: 8px; }
        .cc-filter-fields label { font-size: 13px; color: var(--secondary-text-color); display: flex; align-items: center; gap: 6px; }
        .cc-error { color: var(--error-color, #db4437); font-size: 13px; margin: 4px 0; }
        .cc-new-card { border: 2px dashed var(--divider-color, #ccc); }
        .cc-log-list { display: flex; flex-direction: column; gap: 4px; max-height: 220px; overflow-y: auto; }
        .cc-log-row { display: flex; gap: 10px; font-size: 13px; padding: 4px 0;
          border-bottom: 1px solid var(--divider-color, #eee); }
        .cc-log-row:last-child { border-bottom: none; }
        .cc-log-time { color: var(--secondary-text-color); flex-shrink: 0; white-space: nowrap; }
      </style>
      <h1><ha-icon icon="mdi:motion-sensor"></ha-icon>Cal Activity Sensors</h1>
      <p class="subtitle">Skapar en sensor (aktuellt/nästa event, med ett "active"-attribut för på/av) för ett filtrerat urval av kalenderaktiviteter - eller en nedräkning (dagar kvar) till ett fast datum eller kalenderevent, t.ex. födelsedagar och jubileum.</p>
      <div id="root">Laddar…</div>
    `;
    await this._reload();
  }

  async _reload() {
    const [entriesResp, calendarsResp] = await Promise.all([
      this._hass.callWS({ type: "cal_activity/list_entries" }),
      this._hass.callWS({ type: "cal_activity/list_calendars" }),
    ]);
    this._entries = entriesResp.entries;
    this._calendars = calendarsResp.calendars;
    this._render();
  }

  _calendarName(entityId) {
    const found = this._calendars.find((c) => c.entity_id === entityId);
    return found ? found.name : entityId;
  }

  _render() {
    const root = this.shadowRoot.querySelector("#root");
    root.innerHTML = "";

    if (this._activeKey !== "__new__" && !this._entries.find((e) => e.entry_id === this._activeKey)) {
      this._activeKey = this._entries.length ? this._entries[0].entry_id : "__new__";
    }
    root.appendChild(
      this._renderSubTabs(this._entries, this._activeKey, (key) => {
        this._activeKey = key;
        this._render();
      })
    );
    if (this._activeKey === "__new__") {
      this._safeAppend(root, () => this._renderNewEntryCard(), "ny sensor");
    } else {
      const entry = this._entries.find((e) => e.entry_id === this._activeKey);
      this._safeAppend(root, () => this._renderEntryCard(entry), `sensorn "${entry.name}"`);
    }
  }

  // ---- shared building blocks ----

  /** Renders `build()` into `root`, or a visible error box instead of leaving the tab silently blank. */
  _safeAppend(root, build, context) {
    try {
      root.appendChild(build());
    } catch (err) {
      console.error(`Cal Activity: kunde inte rita ${context}`, err);
      const box = document.createElement("div");
      box.className = "cc-render-error";
      box.textContent = `Kunde inte visa ${context}: ${err.message || err}\n(Se webbläsarens konsol för mer detaljer.)`;
      root.appendChild(box);
    }
  }

  _renderSubTabs(items, activeKey, onSelect) {
    const bar = document.createElement("div");
    bar.className = "cc-subtabs";
    items.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "cc-subtab" + (item.entry_id === activeKey ? " active" : "");
      const icon = document.createElement("ha-icon");
      icon.setAttribute("icon", item.kind === "countdown" ? "mdi:cake-variant" : "mdi:calendar-check");
      btn.appendChild(icon);
      btn.append(item.name);
      btn.onclick = () => onSelect(item.entry_id);
      bar.appendChild(btn);
    });
    const newBtn = document.createElement("button");
    newBtn.type = "button";
    newBtn.className = "cc-subtab cc-subtab-new" + (activeKey === "__new__" ? " active" : "");
    newBtn.innerHTML = `<ha-icon icon="mdi:plus"></ha-icon>`;
    newBtn.onclick = () => onSelect("__new__");
    bar.appendChild(newBtn);
    return bar;
  }

  _buildIconPicker(value) {
    const wrap = document.createElement("div");
    wrap.className = "cc-icon-picker";
    let getValue;
    let usedPicker = false;
    if (customElements.get("ha-icon-picker")) {
      try {
        const picker = document.createElement("ha-icon-picker");
        picker.hass = this._hass;
        picker.label = "Ikon";
        picker.value = value || "";
        wrap.appendChild(picker);
        getValue = () => picker.value || "";
        usedPicker = true;
      } catch (err) {
        console.warn("Cal Activity: ha-icon-picker gick inte att använda, faller tillbaka på textfält", err);
        wrap.innerHTML = "";
      }
    }
    if (!usedPicker) {
      const row = document.createElement("div");
      row.className = "cc-row";
      const icon = document.createElement("ha-icon");
      icon.setAttribute("icon", value || "mdi:help-circle-outline");
      const input = document.createElement("input");
      input.type = "text";
      input.placeholder = "mdi:calendar";
      input.value = value || "";
      input.oninput = () => icon.setAttribute("icon", input.value.trim() || "mdi:help-circle-outline");
      row.appendChild(icon);
      row.appendChild(input);
      wrap.appendChild(row);
      getValue = () => input.value.trim();
    }
    return { element: wrap, getValue };
  }

  // Uploads through Home Assistant's built-in image storage (the same
  // /api/image/upload + /api/image/serve mechanism used by e.g. the Person
  // and Area picture pickers), so images live in HA itself instead of a
  // pasted URL.
  _buildPicturePicker(value) {
    const state = { value: value || "" };
    const wrap = document.createElement("div");
    wrap.className = "cc-picture-picker";

    const row = document.createElement("div");
    row.className = "cc-row";

    const preview = document.createElement("img");
    preview.className = "cc-picture-preview";
    if (state.value) {
      preview.src = state.value;
      preview.style.display = "block";
    }

    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "image/png,image/jpeg,image/gif";
    fileInput.style.display = "none";

    const uploadBtn = document.createElement("button");
    uploadBtn.type = "button";
    uploadBtn.className = "secondary";
    uploadBtn.textContent = state.value ? "Byt bild" : "Ladda upp bild";
    uploadBtn.onclick = () => fileInput.click();

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "secondary";
    removeBtn.textContent = "Ta bort bild";
    removeBtn.style.display = state.value ? "inline-block" : "none";

    const status = document.createElement("span");
    status.className = "cc-picture-status";

    const oldImageId = (url) => {
      const m = /^\/api\/image\/serve\/([^/]+)\/original$/.exec(url || "");
      return m ? m[1] : null;
    };

    const clear = async ({ deleteRemote } = {}) => {
      const previousId = deleteRemote ? oldImageId(state.value) : null;
      state.value = "";
      preview.removeAttribute("src");
      preview.style.display = "none";
      removeBtn.style.display = "none";
      uploadBtn.textContent = "Ladda upp bild";
      if (previousId) {
        try {
          await this._hass.callWS({ type: "image/delete", image_id: previousId });
        } catch (err) {
          // Non-critical cleanup; the reference is gone from our config either way.
          console.warn("Cal Activity: kunde inte städa bort gammal bild", err);
        }
      }
    };

    removeBtn.onclick = () => clear({ deleteRemote: true });

    fileInput.onchange = async () => {
      const file = fileInput.files[0];
      if (!file) return;
      uploadBtn.disabled = true;
      removeBtn.disabled = true;
      status.textContent = "Laddar upp…";
      const previousId = oldImageId(state.value);
      try {
        const fd = new FormData();
        fd.append("file", file);
        const resp = await this._hass.fetchWithAuth("/api/image/upload", {
          method: "POST",
          body: fd,
        });
        if (!resp.ok) {
          throw new Error(resp.status === 413 ? "Bilden är för stor" : `Uppladdning misslyckades (${resp.status})`);
        }
        const item = await resp.json();
        state.value = `/api/image/serve/${item.id}/original`;
        preview.src = state.value;
        preview.style.display = "block";
        removeBtn.style.display = "inline-block";
        uploadBtn.textContent = "Byt bild";
        status.textContent = "";
        if (previousId) {
          try {
            await this._hass.callWS({ type: "image/delete", image_id: previousId });
          } catch (err) {
            console.warn("Cal Activity: kunde inte städa bort gammal bild", err);
          }
        }
      } catch (err) {
        status.textContent = err.message || "Kunde inte ladda upp bilden";
      } finally {
        uploadBtn.disabled = false;
        removeBtn.disabled = false;
        fileInput.value = "";
      }
    };

    row.appendChild(preview);
    row.appendChild(uploadBtn);
    row.appendChild(removeBtn);
    row.appendChild(fileInput);
    wrap.appendChild(row);
    wrap.appendChild(status);

    return { element: wrap, getValue: () => state.value };
  }

  _buildSourcePicker(initialSelected) {
    const state = { selected: [...initialSelected] };
    const wrap = document.createElement("div");

    const chipsWrap = document.createElement("div");
    chipsWrap.className = "cc-chips";

    const pickRow = document.createElement("div");
    pickRow.className = "cc-row";
    const select = document.createElement("select");
    const addBtn = document.createElement("button");
    addBtn.type = "button";
    addBtn.className = "secondary";
    addBtn.textContent = "+ Lägg till";

    const renderChips = () => {
      chipsWrap.innerHTML = "";
      if (!state.selected.length) {
        const empty = document.createElement("span");
        empty.className = "cc-chip-empty";
        empty.textContent = "Inga källkalendrar tillagda ännu";
        chipsWrap.appendChild(empty);
      }
      state.selected.forEach((entityId) => {
        const chip = document.createElement("span");
        chip.className = "cc-chip";
        chip.append(this._calendarName(entityId));
        const rm = document.createElement("button");
        rm.type = "button";
        rm.className = "cc-chip-remove";
        rm.textContent = "×";
        rm.title = "Ta bort källa";
        rm.onclick = () => {
          state.selected = state.selected.filter((id) => id !== entityId);
          renderChips();
          renderSelect();
        };
        chip.appendChild(rm);
        chipsWrap.appendChild(chip);
      });
    };

    const renderSelect = () => {
      select.innerHTML = "";
      const options = this._calendars.filter((c) => !state.selected.includes(c.entity_id));
      if (!options.length) {
        const opt = document.createElement("option");
        opt.textContent = "Inga fler kalendrar att lägga till";
        opt.disabled = true;
        select.appendChild(opt);
        addBtn.disabled = true;
        return;
      }
      addBtn.disabled = false;
      options.forEach((cal) => {
        const opt = document.createElement("option");
        opt.value = cal.entity_id;
        opt.textContent = `${cal.name} (${cal.entity_id})`;
        select.appendChild(opt);
      });
    };

    addBtn.onclick = () => {
      if (select.value && !state.selected.includes(select.value)) {
        state.selected.push(select.value);
        renderChips();
        renderSelect();
      }
    };

    renderChips();
    renderSelect();
    pickRow.appendChild(select);
    pickRow.appendChild(addBtn);
    wrap.appendChild(chipsWrap);
    wrap.appendChild(pickRow);

    return { element: wrap, getSelected: () => state.selected };
  }

  _buildFilterFieldsControls(rule) {
    rule = rule || {};
    const wrap = document.createElement("div");
    wrap.className = "cc-filter-fields";

    const fieldSelect = document.createElement("select");
    ["any", "summary", "description", "location"].forEach((f) => {
      const opt = document.createElement("option");
      opt.value = f;
      opt.textContent = f === "any" ? "Titel + beskrivning + plats" : f;
      if ((rule.field || "any") === f) opt.selected = true;
      fieldSelect.appendChild(opt);
    });

    const includeInput = document.createElement("input");
    includeInput.type = "text";
    includeInput.placeholder = "Inkludera bara event som innehåller (t.ex. Zoo, Djurpark)";
    includeInput.value = (rule.include || []).join(", ");

    const excludeInput = document.createElement("input");
    excludeInput.type = "text";
    excludeInput.placeholder = "Uteslut event som innehåller (t.ex. Zoo, Privat)";
    excludeInput.value = (rule.exclude || []).join(", ");

    const regexLabel = document.createElement("label");
    const regexCb = document.createElement("input");
    regexCb.type = "checkbox";
    regexCb.checked = !!rule.use_regex;
    regexLabel.appendChild(regexCb);
    regexLabel.append(" Tolka orden som regex-mönster");

    const caseLabel = document.createElement("label");
    const caseCb = document.createElement("input");
    caseCb.type = "checkbox";
    caseCb.checked = !!rule.case_sensitive;
    caseLabel.appendChild(caseCb);
    caseLabel.append(" Skiftlägeskänslig");

    wrap.appendChild(fieldSelect);
    wrap.appendChild(includeInput);
    wrap.appendChild(excludeInput);
    wrap.appendChild(regexLabel);
    wrap.appendChild(caseLabel);

    return {
      element: wrap,
      getValues: () => ({
        field: fieldSelect.value,
        include: includeInput.value,
        exclude: excludeInput.value,
        use_regex: regexCb.checked,
        case_sensitive: caseCb.checked,
      }),
    };
  }

  _buildTriggerModeSelect(value) {
    const select = document.createElement("select");
    [
      { value: "active_now", label: "Ett event pågår just nu" },
      { value: "today", label: "Ett event inträffar någon gång idag" },
    ].forEach(({ value: v, label }) => {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = label;
      if ((value || "active_now") === v) opt.selected = true;
      select.appendChild(opt);
    });
    return select;
  }

  _buildKindSelect(value) {
    const select = document.createElement("select");
    [
      { value: "activity", label: "Aktivitet (event pågår just nu / idag)" },
      { value: "countdown", label: "Nedräkning / livshändelse (dagar kvar)" },
    ].forEach(({ value: v, label }) => {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = label;
      if ((value || "activity") === v) opt.selected = true;
      select.appendChild(opt);
    });
    return select;
  }

  _buildDateSourceSelect(value) {
    const select = document.createElement("select");
    [
      { value: "manual", label: "Fast datum" },
      { value: "calendar", label: "Kalenderevent" },
    ].forEach(({ value: v, label }) => {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = label;
      if ((value || "manual") === v) opt.selected = true;
      select.appendChild(opt);
    });
    return select;
  }

  // Everything below the name field for an "activity" kind sensor - shared
  // between the create card and the edit card so the two don't drift apart.
  _buildActivityFieldsSection(entry) {
    entry = entry || {};
    const el = document.createElement("div");

    const iconLabel = document.createElement("div");
    iconLabel.className = "cc-section-title";
    iconLabel.textContent = "Ikon";
    el.appendChild(iconLabel);
    const iconPicker = this._buildIconPicker(entry.icon || "");
    el.appendChild(iconPicker.element);

    const pictureLabel = document.createElement("div");
    pictureLabel.className = "cc-section-title";
    pictureLabel.textContent = "Bild";
    el.appendChild(pictureLabel);
    const picturePicker = this._buildPicturePicker(entry.picture || "");
    el.appendChild(picturePicker.element);

    const sourcesLabel = document.createElement("div");
    sourcesLabel.className = "cc-section-title";
    sourcesLabel.textContent = "Källkalendrar";
    el.appendChild(sourcesLabel);
    const sourcePicker = this._buildSourcePicker(entry.sources || []);
    el.appendChild(sourcePicker.element);

    const filterLabel = document.createElement("div");
    filterLabel.className = "cc-section-title";
    filterLabel.textContent = "Filter";
    el.appendChild(filterLabel);
    const filterControls = this._buildFilterFieldsControls(entry.filter || {});
    el.appendChild(filterControls.element);

    const triggerLabel = document.createElement("div");
    triggerLabel.className = "cc-section-title";
    triggerLabel.textContent = 'Attributet "active" ska vara på när...';
    el.appendChild(triggerLabel);
    const triggerRow = document.createElement("div");
    triggerRow.className = "cc-row";
    const triggerSelect = this._buildTriggerModeSelect(entry.trigger_mode);
    triggerRow.appendChild(triggerSelect);
    el.appendChild(triggerRow);

    return {
      element: el,
      getValues: () => ({
        icon: iconPicker.getValue(),
        picture: picturePicker.getValue(),
        sources: sourcePicker.getSelected(),
        ...filterControls.getValues(),
        trigger_mode: triggerSelect.value,
      }),
    };
  }

  // Everything below the name field for a "countdown" kind sensor. Manual-
  // date and calendar-linked fields are both built up front and toggled with
  // CSS so switching date_source doesn't lose whatever the user already
  // typed into the other block.
  _buildCountdownFieldsSection(entry) {
    entry = entry || {};
    const el = document.createElement("div");

    const iconLabel = document.createElement("div");
    iconLabel.className = "cc-section-title";
    iconLabel.textContent = "Ikon";
    el.appendChild(iconLabel);
    const iconPicker = this._buildIconPicker(entry.icon || "");
    el.appendChild(iconPicker.element);

    const pictureLabel = document.createElement("div");
    pictureLabel.className = "cc-section-title";
    pictureLabel.textContent = "Bild";
    el.appendChild(pictureLabel);
    const picturePicker = this._buildPicturePicker(entry.picture || "");
    el.appendChild(picturePicker.element);

    const sourceLabel = document.createElement("div");
    sourceLabel.className = "cc-section-title";
    sourceLabel.textContent = "Datumkälla";
    el.appendChild(sourceLabel);
    const sourceRow = document.createElement("div");
    sourceRow.className = "cc-row";
    const dateSourceSelect = this._buildDateSourceSelect(entry.date_source);
    sourceRow.appendChild(dateSourceSelect);
    el.appendChild(sourceRow);

    const manualBlock = document.createElement("div");
    const dateRow = document.createElement("div");
    dateRow.className = "cc-row";
    const dateInput = document.createElement("input");
    dateInput.type = "date";
    dateInput.title = "Startdatum";
    dateInput.value = entry.date || "";
    dateRow.appendChild(dateInput);
    const dateEndInput = document.createElement("input");
    dateEndInput.type = "date";
    dateEndInput.title = "Slutdatum (valfritt)";
    dateEndInput.value = entry.date_end || "";
    dateRow.appendChild(dateEndInput);
    manualBlock.appendChild(dateRow);
    const dateEndHint = document.createElement("span");
    dateEndHint.className = "cc-picture-status";
    dateEndHint.textContent = "Slutdatum är valfritt - fyll bara i det för flerdagshändelser som en resa.";
    manualBlock.appendChild(dateEndHint);
    const recurringLabel = document.createElement("label");
    const recurringCb = document.createElement("input");
    recurringCb.type = "checkbox";
    recurringCb.checked = entry.recurring !== false;
    recurringLabel.appendChild(recurringCb);
    recurringLabel.append(" Återkommande varje år (räknar ålder/antal år)");
    manualBlock.appendChild(recurringLabel);

    const calendarBlock = document.createElement("div");
    const calSourcesLabel = document.createElement("div");
    calSourcesLabel.className = "cc-section-title";
    calSourcesLabel.textContent = "Källkalendrar";
    calendarBlock.appendChild(calSourcesLabel);
    const sourcePicker = this._buildSourcePicker(entry.sources || []);
    calendarBlock.appendChild(sourcePicker.element);
    const calFilterLabel = document.createElement("div");
    calFilterLabel.className = "cc-section-title";
    calFilterLabel.textContent = "Filter";
    calendarBlock.appendChild(calFilterLabel);
    const filterControls = this._buildFilterFieldsControls(entry.filter || {});
    calendarBlock.appendChild(filterControls.element);

    el.appendChild(manualBlock);
    el.appendChild(calendarBlock);

    const syncVisibility = () => {
      const isCalendar = dateSourceSelect.value === "calendar";
      manualBlock.style.display = isCalendar ? "none" : "block";
      calendarBlock.style.display = isCalendar ? "block" : "none";
    };
    dateSourceSelect.onchange = syncVisibility;
    syncVisibility();

    return {
      element: el,
      getValues: () => ({
        icon: iconPicker.getValue(),
        picture: picturePicker.getValue(),
        date_source: dateSourceSelect.value,
        date: dateInput.value || "",
        date_end: dateEndInput.value || "",
        recurring: recurringCb.checked,
        sources: sourcePicker.getSelected(),
        ...filterControls.getValues(),
      }),
    };
  }

  _buildActivityLogBox(entryId) {
    const box = document.createElement("div");

    const title = document.createElement("div");
    title.className = "cc-section-title";
    title.textContent = "Senaste händelser";
    box.appendChild(title);

    const list = document.createElement("div");
    list.className = "cc-log-list";
    list.textContent = "Laddar…";
    box.appendChild(list);

    this._hass
      .callWS({ type: "cal_activity/get_activity_log", entry_id: entryId })
      .then((resp) => {
        list.innerHTML = "";
        if (!resp.entries.length) {
          const empty = document.createElement("div");
          empty.className = "cc-chip-empty";
          empty.textContent = "Inga händelser ännu";
          list.appendChild(empty);
          return;
        }
        resp.entries.forEach((item) => {
          const row = document.createElement("div");
          row.className = "cc-log-row";
          const time = document.createElement("span");
          time.className = "cc-log-time";
          time.textContent = new Date(item.time).toLocaleString();
          const msg = document.createElement("span");
          msg.textContent = item.message;
          row.appendChild(time);
          row.appendChild(msg);
          list.appendChild(row);
        });
      })
      .catch((err) => {
        list.textContent = "Kunde inte hämta händelser";
        console.warn("Cal Activity: kunde inte hämta aktivitetslogg", err);
      });

    return box;
  }

  // ---- entry card ----

  _renderEntryCard(entry) {
    const card = document.createElement("div");
    card.className = "cc-card";
    const isCountdown = entry.kind === "countdown";

    const header = document.createElement("div");
    header.className = "cc-card-header";
    const icon = document.createElement("ha-icon");
    icon.setAttribute("icon", entry.icon || (isCountdown ? "mdi:calendar-star" : "mdi:calendar-check"));
    header.appendChild(icon);
    if (entry.picture) {
      const avatar = document.createElement("img");
      avatar.className = "cc-avatar";
      avatar.src = entry.picture;
      header.appendChild(avatar);
    }
    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.className = "cc-name";
    nameInput.value = entry.name;
    header.appendChild(nameInput);
    card.appendChild(header);

    const kindNote = document.createElement("p");
    kindNote.className = "subtitle";
    kindNote.style.margin = "0 0 12px 0";
    kindNote.textContent = isCountdown
      ? "Nedräkning / livshändelse – visar antal dagar kvar till ett fast datum eller kalenderevent. Ange ett slutdatum (eller ett kalenderevent som redan är flera dagar långt) för att sensorn ska vara \"på\" hela perioden, t.ex. en resa."
      : "Aktivitetssensor – visar om ett filtrerat kalenderevent pågår just nu / idag.";
    card.appendChild(kindNote);

    const fieldsSection = isCountdown
      ? this._buildCountdownFieldsSection(entry)
      : this._buildActivityFieldsSection(entry);
    card.appendChild(fieldsSection.element);

    const errorBox = document.createElement("div");
    errorBox.className = "cc-error";
    card.appendChild(errorBox);

    const actions = document.createElement("div");
    actions.className = "cc-actions";

    const saveBtn = document.createElement("button");
    saveBtn.textContent = "Spara";
    saveBtn.onclick = async () => {
      errorBox.textContent = "";
      const values = fieldsSection.getValues();
      try {
        await this._hass.callWS({
          type: "cal_activity/update_entry",
          entry_id: entry.entry_id,
          kind: entry.kind || "activity",
          name: nameInput.value || entry.name,
          ...values,
        });
        await this._reload();
      } catch (err) {
        errorBox.textContent = err.message || "Kunde inte spara ändringarna";
      }
    };

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "danger";
    deleteBtn.textContent = "Ta bort sensor";
    deleteBtn.onclick = async () => {
      if (!confirm(`Ta bort "${entry.name}"? Detta går inte att ångra.`)) return;
      await this._hass.callWS({ type: "cal_activity/delete_entry", entry_id: entry.entry_id });
      await this._reload();
    };

    actions.appendChild(saveBtn);
    actions.appendChild(deleteBtn);
    card.appendChild(actions);

    card.appendChild(this._buildActivityLogBox(entry.entry_id));

    return card;
  }

  _renderNewEntryCard() {
    const card = document.createElement("div");
    card.className = "cc-card cc-new-card";

    const title = document.createElement("div");
    title.className = "cc-section-title";
    title.textContent = "Skapa ny sensor";
    card.appendChild(title);

    const kindRow = document.createElement("div");
    kindRow.className = "cc-row";
    const kindSelect = this._buildKindSelect("activity");
    kindRow.appendChild(kindSelect);
    card.appendChild(kindRow);

    const nameRow = document.createElement("div");
    nameRow.className = "cc-row";
    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.placeholder = "Namn, t.ex. Zoo-besök eller Mammas födelsedag";
    nameRow.appendChild(nameInput);
    card.appendChild(nameRow);

    const fieldsContainer = document.createElement("div");
    card.appendChild(fieldsContainer);

    let fieldsSection = null;
    const renderFields = () => {
      fieldsContainer.innerHTML = "";
      fieldsSection =
        kindSelect.value === "countdown"
          ? this._buildCountdownFieldsSection({})
          : this._buildActivityFieldsSection({});
      fieldsContainer.appendChild(fieldsSection.element);
    };
    kindSelect.onchange = renderFields;
    renderFields();

    const errorBox = document.createElement("div");
    errorBox.className = "cc-error";
    card.appendChild(errorBox);

    const createBtn = document.createElement("button");
    createBtn.textContent = "Skapa sensor";
    createBtn.onclick = async () => {
      errorBox.textContent = "";
      if (!nameInput.value.trim()) {
        errorBox.textContent = "Ange ett namn";
        return;
      }
      const kind = kindSelect.value;
      const values = fieldsSection.getValues();
      if (kind === "activity" && !values.sources.length) {
        errorBox.textContent = "Välj minst en källkalender";
        return;
      }
      if (kind === "countdown") {
        if (values.date_source === "manual" && !values.date) {
          errorBox.textContent = "Ange ett datum";
          return;
        }
        if (values.date_source === "manual" && values.date_end && values.date_end < values.date) {
          errorBox.textContent = "Slutdatumet kan inte vara före startdatumet";
          return;
        }
        if (values.date_source === "calendar" && !values.sources.length) {
          errorBox.textContent = "Välj minst en källkalender";
          return;
        }
      }
      try {
        const result = await this._hass.callWS({
          type: "cal_activity/create_entry",
          kind,
          name: nameInput.value.trim(),
          ...values,
        });
        this._activeKey = result.entry_id;
        await this._reload();
      } catch (err) {
        errorBox.textContent = err.message || "Kunde inte skapa sensorn";
      }
    };
    card.appendChild(createBtn);

    return card;
  }
}

customElements.define("cal-activity-panel", CalActivityPanel);
