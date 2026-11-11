(async () => { await until(() => E.res);
  engNodeClick("a3", {}); await W(400);
  for (let i = 0; i < 3; i++) { engGroundedStep(); await W(300); }
  await W(900); done(); })();
