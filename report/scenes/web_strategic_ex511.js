(async () => { document.querySelector('[data-tab=strategic]').click(); await until(() => T.inst);
  await pick("#st-example", "1"); await W(400);
  await stCheck(); await W(200); document.querySelector(".viol").click(); await W(1600);
  await stBest("x"); await W(500); done(); })();
