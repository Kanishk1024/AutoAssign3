(async () => { await until(() => E.res); await pick("#eng-example", "1");
  await until(() => E.res && E.graph.name === "Figure 5.2"); await W(300);
  engShowLab(1); await W(900); done(); })();
