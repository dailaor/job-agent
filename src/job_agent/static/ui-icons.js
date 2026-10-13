/* Small, local, consistent geometric icons; no runtime dependency or remote assets. */
window.JobIcons = (() => {
  const shapes = {
    spark: '<path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6Z"/>',
    home: '<path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/>',
    briefcase: '<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V3h8v4M3 12a24 24 0 0 0 18 0M10 12v3h4v-3"/>',
    document: '<path d="M14 3H5v18h14V8Z"/><path d="M14 3v5h5M8 12h8M8 16h6"/>',
    book: '<path d="M12 5c-3-2-6-2-9-1v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-3-1-6-1-9 1Z"/><path d="M12 5v15"/>',
    settings: '<path d="m9 3-1 3-3 1-2 4 2 3 1 4 4 1 2 2 4-2 3-1 2-4-2-3-1-4-4-1-2-2Z"/><circle cx="12" cy="12" r="3"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    refresh: '<path d="M20 8a8 8 0 1 0 0 8M20 3v5h-5"/>',
    external: '<path d="M14 3h7v7M21 3l-9 9M10 3H3v18h18v-7"/>',
    arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    chevron: '<path d="m9 5 7 7-7 7"/>',
    chevronLeft: '<path d="m15 5-7 7 7 7"/>',
    chevronRight: '<path d="m9 5 7 7-7 7"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    warning: '<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 17h.01"/>',
    shield: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
    money: '<circle cx="12" cy="12" r="9"/><path d="M15 8h-4a2 2 0 0 0 0 4h2a2 2 0 0 1 0 4H9M12 6v12"/>',
    chart: '<path d="M5 20v-6M12 20V9M19 20V4"/>',
    pace: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    users: '<circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6M18 16a5 5 0 0 1 3 5"/>',
    growth: '<path d="m3 17 6-6 4 3 8-10M15 4h6v6"/>',
    location: '<path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 0 1 14 0Z"/><circle cx="12" cy="10" r="2"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>'
  };
  return {icon(name) {
    return `<svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${shapes[name] || shapes.document}</svg>`;
  }};
})();
