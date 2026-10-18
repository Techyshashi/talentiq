/** Shared accessible status surface for AI work. */
export function createAILoader(label = 'Working with TalentIQ') {
  const box = document.createElement('section');
  box.className = 'ai-loader';
  box.setAttribute('role', 'status');
  box.setAttribute('aria-live', 'polite');
  const spinner = document.createElement('span');
  spinner.className = 'spinner';
  spinner.setAttribute('aria-hidden', 'true');
  const message = document.createElement('span');
  message.textContent = label;
  const progress = document.createElement('progress');
  progress.max = 100;
  progress.value = 0;
  progress.setAttribute('aria-label', 'AI task progress');
  box.append(spinner, message, progress);
  return {
    element: box,
    update(text, value) { message.textContent = text; if (value !== undefined) progress.value = value; },
    complete(text = 'Complete') { spinner.remove(); progress.value = 100; message.textContent = text; },
    fail(text, retry) {
      box.classList.add('loader-error');
      message.textContent = text;
      progress.remove();
      if (retry) { const button = document.createElement('button'); button.type = 'button'; button.className = 'ghost retry'; button.textContent = 'Try again'; button.onclick = retry; box.append(button); }
    }
  };
}

export function nimoMessage(message) {
  const note = document.createElement('p');
  note.className = 'notice';
  note.setAttribute('role', 'status');
  note.textContent = `Nimo: ${message}`;
  return note;
}
