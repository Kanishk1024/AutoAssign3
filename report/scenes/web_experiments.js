(async () => { await until(() => E.res); document.querySelector('[data-tab=experiments]').click(); await W(1800); done(); })();
