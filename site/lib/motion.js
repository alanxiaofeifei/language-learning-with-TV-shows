export function initMotion() {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  const apply = () => {
    const on = !reduce.matches;
    document.documentElement.classList.toggle("motion-ready", on);
    document.documentElement.classList.toggle("reduce-motion", !on);
  };
  apply();
  reduce.addEventListener("change", apply);
}

export function motionOn() {
  return document.documentElement.classList.contains("motion-ready");
}

export function splitChars(el, text) {
  el.setAttribute("aria-label", text);
  el.textContent = "";
  let i = 0;
  for (const word of text.split(/(\s+)/)) {
    if (/^\s+$/.test(word) || word === "") {
      el.append(document.createTextNode(word));
      continue;
    }
    const wrap = document.createElement("span");
    wrap.style.whiteSpace = "nowrap";
    wrap.setAttribute("aria-hidden", "true");
    for (const ch of word) {
      const s = document.createElement("span");
      s.className = "ch";
      s.style.setProperty("--i", String(i++));
      s.textContent = ch;
      wrap.append(s);
    }
    el.append(wrap);
  }
  return el;
}

export function paintMain(main, nodes) {
  main.getAnimations().forEach((a) => a.cancel());
  const list = [nodes].flat().filter(Boolean);
  main.replaceChildren(...list);
  main.dataset.ready = "1";
  main.querySelectorAll(".reveal").forEach((el, i) => el.style.setProperty("--i", String(Math.min(i, 8))));
  bindTilt(main);
}

export async function swapMain(main, nodes) {
  if (!motionOn() || !main.dataset.ready) {
    paintMain(main, nodes);
    return;
  }
  try {
    const out = main.animate(
      [{ opacity: 1, transform: "translateY(0)" }, { opacity: 0, transform: "translateY(-18px)" }],
      { duration: 200, easing: "cubic-bezier(.2,.7,.2,1)" },
    );
    await out.finished;
  } catch { /* cancelled */ }
  paintMain(main, nodes);
  main.animate(
    [{ opacity: 0, transform: "translateY(28px)" }, { opacity: 1, transform: "translateY(0)" }],
    { duration: 520, easing: "cubic-bezier(.16,1,.3,1)" },
  );
}

export function bindTilt(root) {
  if (!motionOn() || !window.matchMedia("(pointer: fine)").matches) return;
  root.querySelectorAll("[data-tilt]").forEach((el) => {
    el.addEventListener("pointermove", (e) => {
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      el.style.transform = `rotateY(${(x * 7).toFixed(2)}deg) rotateX(${(-y * 7).toFixed(2)}deg) translateY(-6px)`;
    });
    el.addEventListener("pointerleave", () => { el.style.transform = ""; });
  });
}
