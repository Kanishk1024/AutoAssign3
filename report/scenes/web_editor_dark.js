(async () => { await until(() => E.res); await pick("#eng-example", "blank"); await W(300);
  document.querySelector('[data-mode=edit]').click();
  engBackground([200, 200]); await W(250); engBackground([550, 200]); await W(250); engBackground([380, 450]); await W(250);
  const [a, b, c] = E.graph.args;
  engNodeClick(a, {}); engNodeClick(b, {}); await W(250); engNodeClick(b, {}); engNodeClick(c, {}); await W(250);
  engNodeClick(c, {}); engNodeClick(a, {}); await W(250); engNodeClick(b, {}); engNodeClick(b, {}); await W(400);
  engBackground([650, 450]); await W(300); const d = E.graph.args[3]; engNodeClick(d, {}); engNodeClick(a, {}); await W(400);
  engSetView({ type: "lab" }); await W(900); done(); })();
