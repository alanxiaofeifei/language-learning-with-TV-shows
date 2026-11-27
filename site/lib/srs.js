// Spaced repetition (SM-2 family, 4 grades). Pure functions; state lives in localStorage via app.js.
export const GRADES = ["again", "hard", "good", "easy"];

export function today(now = new Date()) {
  return Math.floor((now.getTime() - now.getTimezoneOffset() * 60000) / 86400000);
}

export function newCard() {
  return { reps: 0, lapses: 0, ease: 2.5, interval: 0, due: 0 };
}

export function review(card, grade, day = today()) {
  const c = { ...(card || newCard()) };
  const g = GRADES.indexOf(grade);
  if (g < 0) throw new Error("bad grade " + grade);
  if (g === 0) {
    c.lapses += 1; c.reps = 0; c.interval = 0; c.ease = Math.max(1.3, c.ease - 0.2);
    c.due = day;              // again: show again today
  } else {
    c.ease = Math.max(1.3, c.ease + [0, -0.15, 0, 0.15][g]);
    if (c.reps === 0) c.interval = [0, 1, 1, 3][g];
    else if (c.reps === 1) c.interval = [0, 2, 3, 6][g];
    else c.interval = Math.max(c.interval + 1, Math.round(c.interval * (g === 1 ? 1.2 : c.ease) * (g === 3 ? 1.3 : 1)));
    c.reps += 1; c.due = day + c.interval;
  }
  c.last = day;
  return c;
}

// Cards due today (oldest first), then up to `newLimit` unseen cards in the given order.
export function queue(ids, states, { day = today(), newLimit = 15, newSeenToday = 0 } = {}) {
  const due = ids.filter((id) => states[id] && states[id].due <= day).sort((a, b) => states[a].due - states[b].due);
  const fresh = ids.filter((id) => !states[id]).slice(0, Math.max(0, newLimit - newSeenToday));
  return { due, fresh };
}
