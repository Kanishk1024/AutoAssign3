(async () => { document.querySelector('[data-tab=strategic]').click();
  await until(() => T.inst && T.util.x !== undefined);
  await stCheck(); await stManipulate(); await W(900); done(); })();
