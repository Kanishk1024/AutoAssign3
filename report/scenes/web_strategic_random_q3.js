/* find a random instance that is strategyproof although the Thm 5.4 condition fails,
   whose reason is the "alpha6 effect" (hiding loses other own arguments) */
(async () => { document.querySelector('[data-tab=strategic]').click(); await until(() => T.inst);
  for (let seed = 1; seed < 400; seed++) {
    const inst = await api("/api/random", { p: 0.25, self_attacks: true, seed });
    if (inst.args.length > 7) continue;
    const c = await api("/api/strategic", { args: inst.args, attacks: inst.attacks, types: inst.types });
    if (c.violations.length <= 4 && c.strategyproof && !c.cond_walk && c.diagnosis && c.diagnosis.subcategory === "other-own-argument-lost") {
      inst.name = `Random instance (p=0.25, seed ${seed})`;
      const o = document.createElement("option"); o.value = "random"; o.textContent = inst.name;
      document.querySelector("#st-example").append(o); document.querySelector("#st-example").value = "random";
      stLoad(inst); await W(500); await stCheck(); await W(300);
      document.querySelector(".viol").click(); await W(1800); break;
    }
  }
  done(); })();
